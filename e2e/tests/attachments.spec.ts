import { expect, test } from '../fixtures';

/**
 * Files linked from a page's body are listed as downloads on the
 * published page, above the text, in a collapsible "Files" list. Nothing is stored beside the content: the list is read from
 * its links, so it follows the page through change requests.
 */
test.describe('Page attachments', () => {
	test('the published page lists linked files but not inline images', async ({
		page,
		wiki,
	}) => {
		const space = await wiki.space({
			pages: [
				{
					title: 'Attachment Host',
					content: [
						'Download the [Verifier manual](/files/verifier-manual.pdf) and',
						'the [site config](/files/common_site_config.json).',
						'',
						'![inline shot](/files/shot.png)',
					].join('\n'),
				},
			],
		});
		const host = space.page('Attachment Host');

		await page.setViewportSize({ width: 1280, height: 900 });
		await page.goto(`/${host.route}`);

		const section = page.locator('#wiki-attachments');
		await expect(section).toContainText('Verifier manual');
		await expect(section).toContainText('site config');
		await expect(section.locator('a[download]')).toHaveCount(2);
		await expect(section).not.toContainText('shot.png');
		await expect(
			section.locator('a[href="/files/verifier-manual.pdf"]'),
		).toBeVisible();
	});

	test('a page with no linked files has no attachments section', async ({
		page,
		wiki,
	}) => {
		const space = await wiki.space({
			pages: [{ title: 'No Files', content: 'Nothing to download here.' }],
		});

		await page.goto(`/${space.page('No Files').route}`);

		await expect(page.locator('#wiki-attachments')).toBeHidden();
	});
});
