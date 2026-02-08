#!/usr/bin/env node

/**
 * Bundle Python runtime for Electron packaging.
 *
 * Downloads standalone Python builds from python-build-standalone
 * and installs pip dependencies into the bundled environment.
 *
 * Usage:
 *   node scripts/bundle-python.js [--platform mac|win] [--arch x64|arm64]
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const https = require('https');

// Python version to bundle
const PYTHON_VERSION = '3.11.7';
const PBS_RELEASE = '20240107';

// python-build-standalone release URLs
const BUILDS = {
    'darwin-arm64': `https://github.com/indygreg/python-build-standalone/releases/download/${PBS_RELEASE}/cpython-${PYTHON_VERSION}+${PBS_RELEASE}-aarch64-apple-darwin-install_only.tar.gz`,
    'darwin-x64': `https://github.com/indygreg/python-build-standalone/releases/download/${PBS_RELEASE}/cpython-${PYTHON_VERSION}+${PBS_RELEASE}-x86_64-apple-darwin-install_only.tar.gz`,
    'win32-x64': `https://github.com/indygreg/python-build-standalone/releases/download/${PBS_RELEASE}/cpython-${PYTHON_VERSION}+${PBS_RELEASE}-x86_64-pc-windows-msvc-shared-install_only.tar.gz`,
};

const OUTPUT_DIR = path.join(__dirname, '..', 'electron', 'python');
const REQUIREMENTS = path.join(__dirname, '..', 'requirements-electron.txt');

function getPlatformKey() {
    const args = process.argv.slice(2);
    let platform = process.platform;
    let arch = process.arch;

    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--platform') {
            const val = args[i + 1];
            platform = val === 'mac' ? 'darwin' : val === 'win' ? 'win32' : val;
        }
        if (args[i] === '--arch') arch = args[i + 1];
    }

    return `${platform}-${arch}`;
}

function downloadFile(url, dest) {
    return new Promise((resolve, reject) => {
        console.log(`Downloading: ${url}`);
        console.log(`To: ${dest}`);

        const follow = (url) => {
            https.get(url, (res) => {
                if (res.statusCode === 301 || res.statusCode === 302) {
                    follow(res.headers.location);
                    return;
                }
                if (res.statusCode !== 200) {
                    reject(new Error(`HTTP ${res.statusCode}`));
                    return;
                }

                const totalBytes = parseInt(res.headers['content-length'], 10) || 0;
                let downloaded = 0;

                const file = fs.createWriteStream(dest);
                res.on('data', (chunk) => {
                    downloaded += chunk.length;
                    if (totalBytes > 0) {
                        const pct = ((downloaded / totalBytes) * 100).toFixed(1);
                        process.stdout.write(`\r  Progress: ${pct}% (${(downloaded / 1024 / 1024).toFixed(1)} MB)`);
                    }
                });
                res.pipe(file);
                file.on('finish', () => {
                    process.stdout.write('\n');
                    file.close(resolve);
                });
            }).on('error', reject);
        };

        follow(url);
    });
}

async function main() {
    const platformKey = getPlatformKey();
    const url = BUILDS[platformKey];

    if (!url) {
        console.error(`No Python build available for platform: ${platformKey}`);
        console.error(`Available platforms: ${Object.keys(BUILDS).join(', ')}`);
        process.exit(1);
    }

    console.log(`\n=== Bundling Python for ${platformKey} ===\n`);

    // Clean output directory
    if (fs.existsSync(OUTPUT_DIR)) {
        console.log(`Cleaning existing Python bundle at ${OUTPUT_DIR}...`);
        fs.rmSync(OUTPUT_DIR, { recursive: true, force: true });
    }
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });

    // Download
    const tarball = path.join(OUTPUT_DIR, 'python.tar.gz');
    await downloadFile(url, tarball);

    // Extract
    console.log('\nExtracting Python...');
    execSync(`tar -xzf "${tarball}" -C "${OUTPUT_DIR}" --strip-components=1`, { stdio: 'inherit' });

    // Remove tarball
    fs.unlinkSync(tarball);

    // Find the Python binary
    const isWindows = platformKey.startsWith('win32');
    const pythonBin = isWindows
        ? path.join(OUTPUT_DIR, 'python.exe')
        : path.join(OUTPUT_DIR, 'bin', 'python3');

    if (!fs.existsSync(pythonBin)) {
        console.error(`Python binary not found at: ${pythonBin}`);
        console.error('Directory contents:');
        execSync(`ls -la "${OUTPUT_DIR}"`, { stdio: 'inherit' });
        process.exit(1);
    }

    console.log(`Python binary: ${pythonBin}`);

    // Install pip dependencies
    console.log('\nInstalling Python dependencies...');
    const isCrossBuild = isWindows !== (process.platform === 'win32');

    try {
        if (isCrossBuild) {
            // Cross-compilation: can't run the target python binary on this OS
            // Use host python to download platform-specific wheels, then extract them
            console.log('Cross-platform build detected - using pip download for target platform...');

            // Determine target site-packages path
            const sitePackages = isWindows
                ? path.join(OUTPUT_DIR, 'Lib', 'site-packages')
                : path.join(OUTPUT_DIR, 'lib', `python${PYTHON_VERSION.split('.').slice(0, 2).join('.')}`, 'site-packages');

            fs.mkdirSync(sitePackages, { recursive: true });

            // Determine pip platform tag for the target
            const pipPlatform = isWindows ? 'win_amd64' : 'manylinux2014_x86_64';
            const pyVer = PYTHON_VERSION.split('.').slice(0, 2).join('.');

            // Use host python3 to download ALL wheels (including deps) for the target platform
            const tmpWheelDir = path.join(OUTPUT_DIR, '_wheels');
            fs.mkdirSync(tmpWheelDir, { recursive: true });

            execSync(
                `python3 -m pip download -r "${REQUIREMENTS}" ` +
                `--dest "${tmpWheelDir}" ` +
                `--platform ${pipPlatform} ` +
                `--python-version ${pyVer} ` +
                `--implementation cp ` +
                `--only-binary=:all:`,
                { stdio: 'inherit' }
            );

            // Extract all .whl files (they're just zip files) into site-packages
            console.log(`\nExtracting wheels into ${sitePackages}...`);
            const wheels = fs.readdirSync(tmpWheelDir).filter(f => f.endsWith('.whl'));
            for (const whl of wheels) {
                console.log(`  Extracting: ${whl}`);
                execSync(`unzip -qo "${path.join(tmpWheelDir, whl)}" -d "${sitePackages}"`, { stdio: 'inherit' });
            }

            // Clean up wheel cache
            fs.rmSync(tmpWheelDir, { recursive: true, force: true });
        } else {
            // Native build: can run the bundled python directly
            execSync(`"${pythonBin}" -m pip install --upgrade pip`, { stdio: 'inherit' });
            execSync(`"${pythonBin}" -m pip install -r "${REQUIREMENTS}"`, { stdio: 'inherit' });
        }
    } catch (err) {
        console.error('Failed to install dependencies:', err.message);
        process.exit(1);
    }

    // Report size
    const sizeOutput = execSync(`du -sh "${OUTPUT_DIR}"`).toString().trim();
    console.log(`\nBundled Python size: ${sizeOutput.split('\t')[0]}`);
    console.log('\nPython bundling complete!');
}

main().catch((err) => {
    console.error('Fatal error:', err);
    process.exit(1);
});
