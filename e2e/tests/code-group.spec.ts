import { expect, test } from '../fixtures';

/**
 * A `:::code-group` of fences is one block with tabs on the published page.
 * Tab titles come from the fence label (```json site_config.json), else the
 * language.
 */
test.describe('Code group', () => {
	test('the published page shows fences as tabs and switches between them', async ({
		page,
		wiki,
	}) => {
		const space = await wiki.space({
			pages: [
				{
					title: 'Code Group Host',
					content: [
						':::code-group',
						'```bash',
						'bench restart',
						'```',
						'```json site_config.json',
						'{"developer_mode": 1}',
						'```',
						':::',
					].join('\n'),
				},
			],
		});

		await page.setViewportSize({ width: 1280, height: 900 });
		await page.goto(`/${space.page('Code Group Host').route}`);

		const tabs = page.locator('.wiki-code-group-tab');
		await expect(tabs).toHaveText(['bash', 'site_config.json']);
		await expect(page.locator('.wiki-code-group pre:visible')).toHaveCount(1);
		await expect(page.locator('.wiki-code-group pre:visible')).toContainText(
			'bench restart',
		);

		await tabs.nth(1).click();
		await expect(page.locator('.wiki-code-group pre:visible')).toContainText(
			'developer_mode',
		);
	});
});
