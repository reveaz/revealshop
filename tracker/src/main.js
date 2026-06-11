import { PlaywrightCrawler, Configuration, log as crawleeLog } from 'crawlee';
import { launchOptions } from 'camoufox-js';
import { firefox } from 'playwright';

process.env.CRAWLEE_LOG_LEVEL = 'OFF';
crawleeLog.setLevel(crawleeLog.LEVELS.OFF);

const trackNumber = process.argv[2];

if (!trackNumber) {
    console.error('Usage: node src/main.js <TRACK_NUMBER>');
    process.exit(1);
}

const url = `https://www.17track.net/ru/track?nums=${trackNumber}`;

Configuration.getGlobalConfig().set('persistStorage', false);

const camoufoxOpts = await launchOptions({
    headless: true,
    os: 'windows',
});

const crawler = new PlaywrightCrawler({
    launchContext: {
        launcher: firefox,
        launchOptions: {
            ...camoufoxOpts,
            timeout: 60_000,
        },
    },
    navigationTimeoutSecs: 60,
    requestHandlerTimeoutSecs: 120,
    maxRequestRetries: 1,
    headless: true,

    async requestHandler({ page }) {

        await page.waitForTimeout(5000);

        const cfChallenge = page.locator('#challenge-running, #challenge-form, .cf-browser-verification');
        try {
            await cfChallenge.first().waitFor({ state: 'visible', timeout: 3000 });
            await page.waitForURL(/17track\.net\/ru\/track/, { timeout: 45_000 });
            await page.waitForTimeout(3000);
        } catch {
        }

        const resultContainer = page.locator('.yqcr-main, .res-content, [id*="YQ_TrackResult"], .trck');
        try {
            await resultContainer.first().waitFor({ state: 'visible', timeout: 30_000 });
        } catch {
        }

        await page.waitForTimeout(8000);

        const text = await page.evaluate((tn) => {
            const body = document.body.innerText || '';
            const lines = body.split('\n').map(l => l.trim()).filter(Boolean);

            let start = -1;
            for (let i = 0; i < lines.length; i++) {
                if (lines[i].includes(tn)) {
                    start = i;
                    break;
                }
            }

            if (start === -1) {
                const altNames = ['TestNumber00017'];
                for (let i = 0; i < lines.length; i++) {
                    for (const alt of altNames) {
                        if (lines[i].includes(alt)) {
                            start = i;
                            break;
                        }
                    }
                    if (start !== -1) break;
                }
            }

            if (start === -1) return '';

            const stopPatterns = [
                /^😊/,
                /^Welcome/i,
                /^Please input/i,
                /^Clear all numbers/i,
                /^Extract numbers/i,
                /^Select shipping/i,
                /^\(Автоматическое/,
                /^TRACK$/,
                /^Backward Skip/i,
                /^Play Video/i,
                /^Forward Skip/i,
                /^Advertisement$/i,
                /^X$/,
            ];

            const skipPatterns = [
                /^FAQ>$/,
                /^More info$/,
                /^Копировать файлы$/,
                /^Копировать ссылку$/,
                /^Перевести:$/,
                /^Русский$/,
                /^Call$/,
                /^\+\d+\s\(\d+\)/,
            ];

            const result = [];
            for (let i = start; i < lines.length; i++) {
                const line = lines[i];
                if (stopPatterns.some(p => p.test(line))) break;
                if (skipPatterns.some(p => p.test(line))) continue;
                result.push(line);
            }

            return result.join('\n');
        }, trackNumber);

        if (text.trim()) {
            console.log(text.trim());
        } else {
            console.error('ERROR: tracking data not found on page');
            process.exit(1);
        }
    },

    async failedRequestHandler({ request }) {
        console.error('ERROR: failed to load tracking page');
        process.exit(1);
    },
});

await crawler.run([url]);
