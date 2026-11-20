"""Check the shared pstack assets against the Devin plugin layout."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DevinPluginTest(unittest.TestCase):
    def test_manifest_and_shared_metadata(self):
        manifest = json.loads((ROOT / '.devin-plugin/plugin.json').read_text())
        existing = json.loads((ROOT / 'plugin.json').read_text())
        self.assertRegex(manifest['name'], r'^[a-z0-9]+(?:[.-][a-z0-9]+)*$')
        for field in ('name', 'version', 'description', 'author', 'homepage',
                      'repository', 'license', 'keywords'):
            self.assertEqual(manifest[field], existing[field], field)
        self.assertTrue((ROOT / manifest['logo']).is_file())
        self.assertNotIn('skills', manifest)  # Devin discovers the shared skills/ tree by default.

    def test_skills_are_discoverable_and_named(self):
        skills = list((ROOT / 'skills').glob('*/SKILL.md'))
        self.assertGreater(len(skills), 0)
        for skill in skills:
            with self.subTest(skill=skill.parent.name):
                text = skill.read_text()
                self.assertTrue(text.startswith('---\n'))
                self.assertRegex(text.split('---', 2)[1],
                                 rf'(?m)^name:\s*["\']?{re.escape(skill.parent.name)}["\']?\s*$')

    def test_agents_use_portable_frontmatter(self):
        for name in ('poteto-agent', 'comment-sicko'):
            with self.subTest(agent=name):
                text = (ROOT / 'agents' / f'{name}.md').read_text()
                self.assertTrue(text.startswith('---\n'))
                frontmatter = text.split('---', 2)[1]
                self.assertRegex(frontmatter, rf'(?m)^name:\s*{name}\s*$')
                self.assertRegex(frontmatter, r'(?m)^description:\s*\S')
                self.assertNotRegex(frontmatter, r'(?m)^model:')

    def test_devin_harness_fallbacks_exist(self):
        self.assertTrue((ROOT / 'docs/harness/devin.md').is_file())
        self.assertTrue((ROOT / 'skills/no-comments/references/comment-sicko.md').is_file())
        self.assertTrue((ROOT / 'skills/poteto-mode/worker.md').is_file())
        for name in ('arena', 'interrogate', 'no-comments', 'poteto-help',
                     'poteto-mode', 'setup-pstack', 'swarm'):
            with self.subTest(skill=name):
                text = (ROOT / 'skills' / name / 'SKILL.md').read_text()
                self.assertIn('docs/harness/devin.md', text)
        self.assertIn('subagent_explore', (ROOT / 'skills/how/SKILL.md').read_text())


if __name__ == '__main__':
    unittest.main()
