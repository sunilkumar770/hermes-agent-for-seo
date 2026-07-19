"""
GitHub Deployment Agent
Validates, commits, and pushes SEO changes with proper commit messages
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from agents.base import BaseAgent, AgentResult


class GitHubDeploymentAgent(BaseAgent):
    """Agent for validating, committing, and pushing SEO changes"""

    def __init__(self, name: str, config: Dict[str, Any], project_root: Path):
        super().__init__(name, config, project_root)
        self.deploy_config = config.get('agents', {}).get('github_deployment', {})
        self.repo = self.deploy_config.get('repo', 'gorentals/seo-content')
        self.branch = self.deploy_config.get('branch', 'seo-automation')
        self.validation = self.deploy_config.get('validation', [
            'markdown_lint', 'metadata_validation', 'schema_validation',
            'link_check', 'image_optimization'
        ])
        self.commit_types = self.deploy_config.get('commit_types', [
            'feat(seo)', 'feat(blog)', 'fix(metadata)', 'fix(schema)',
            'docs(seo)', 'refactor(seo)', 'chore(seo)'
        ])

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute GitHub deployment"""
        # Get changed files from context
        changed_files = context.get('changed_files', [])
        
        if not changed_files:
            # Auto-detect changes
            changed_files = self._detect_changes()
        
        if not changed_files:
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={'message': 'No changes to deploy', 'deployed': False}
            )
        
        # Validate files
        validation_results = self._validate_files(changed_files)
        
        if not validation_results['valid']:
            return AgentResult(
                agent_name=self.name,
                success=False,
                errors=validation_results['errors'],
                data={'validated': False, 'errors': validation_results['errors']}
            )
        
        # Stage changes
        stage_result = self._stage_files(changed_files)
        
        if not stage_result['success']:
            return AgentResult(
                agent_name=self.name,
                success=False,
                errors=stage_result['errors'],
                data={'staged': False}
            )
        
        # Generate commit message
        commit_msg = self._generate_commit_message(changed_files)
        
        # Commit
        commit_result = self._commit(commit_msg)
        
        if not commit_result['success']:
            return AgentResult(
                agent_name=self.name,
                success=False,
                errors=commit_result['errors'],
                data={'committed': False}
            )
        
        # Push (optional - controlled by config)
        push_result = {'success': True, 'pushed': False}
        if self.deploy_config.get('auto_push', False):
            push_result = self._push()
        
        # Create PR info
        pr_info = self._generate_pr_info(changed_files, commit_msg)
        
        # Save deployment log
        files_created = []
        deploy_log = self.save_json({
            'deployed_at': datetime.now().isoformat(),
            'commit_hash': commit_result.get('commit_hash', ''),
            'commit_message': commit_msg,
            'files_changed': changed_files,
            'validation': validation_results,
            'pushed': push_result.get('pushed', False),
            'pr_info': pr_info
        }, "deployment-log.json")
        files_created.append(deploy_log)
        
        # Markdown report
        report = self._generate_report(changed_files, validation_results, commit_result, push_result, pr_info)
        report_file = self.save_output(report, "deployment-report.md")
        files_created.append(report_file)
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                'deployed': True,
                'commit_hash': commit_result.get('commit_hash', ''),
                'files_changed': len(changed_files),
                'pushed': push_result.get('pushed', False),
                'pr_url': pr_info.get('pr_url', '')
            },
            files_created=files_created
        )

    def _detect_changes(self) -> List[str]:
        """Detect changed files using git status from git repo root"""
        try:
            # First find the git repo root
            git_root_result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=10
            )
            if git_root_result.returncode != 0:
                return []
            git_root = Path(git_root_result.stdout.strip())
            
            # Run git status from the git repo root
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=git_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30
            )
            if result.returncode == 0:
                files = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        if len(line) >= 3:
                            status = line[:2]
                            filepath = line[3:].strip()
                            index_status = status[0]
                            worktree_status = status[1]
                            if index_status in ['M', 'A', 'D', 'R', 'C'] or worktree_status in ['M', 'A', 'D', 'R', 'C'] or status == '??':
                                # Validate the path doesn't contain weird characters
                                if filepath and not any(ord(c) > 127 for c in filepath):
                                    # Check if the file is within the project_root
                                    full_path = git_root / filepath
                                    try:
                                        full_path.resolve().relative_to(self.project_root.resolve())
                                        # Return path relative to project_root
                                        rel_path = full_path.relative_to(self.project_root)
                                        files.append(str(rel_path))
                                    except (ValueError, OSError):
                                        # File is outside project_root, skip it
                                        pass
                return files
        except Exception as e:
            self.logger.error(f"Error detecting changes: {e}")
        return []

    def _validate_files(self, files: List[str]) -> Dict[str, Any]:
        """Validate changed files"""
        errors = []
        warnings = []
        
        for filepath in files:
            # Additional validation: ensure path is relative and doesn't contain suspicious patterns
            if '..' in filepath or filepath.startswith('/') or filepath.startswith('\\'):
                errors.append(f"Suspicious path: {filepath}")
                continue
            
            full_path = self.project_root / filepath
            
            # Verify the resolved path is within project root
            try:
                full_path.resolve().relative_to(self.project_root.resolve())
            except (ValueError, OSError):
                errors.append(f"Path outside project root: {filepath}")
                continue
            
            if not full_path.exists():
                errors.append(f"File not found: {filepath}")
                continue
            
            # Markdown lint
            if filepath.endswith('.md'):
                validation = self._validate_markdown(full_path)
                errors.extend(validation['errors'])
                warnings.extend(validation['warnings'])
            
            # JSON validation
            elif filepath.endswith('.json'):
                validation = self._validate_json(full_path)
                errors.extend(validation['errors'])
                warnings.extend(validation['warnings'])
            
            # Image optimization check
            elif filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                validation = self._validate_image(full_path)
                errors.extend(validation['errors'])
                warnings.extend(validation['warnings'])
            
            # YAML frontmatter validation for markdown
            if filepath.endswith('.md'):
                fm_validation = self._validate_frontmatter(full_path)
                errors.extend(fm_validation['errors'])
                warnings.extend(fm_validation['warnings'])
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'files_checked': len(files)
        }

    def _validate_markdown(self, filepath: Path) -> Dict[str, List[str]]:
        """Basic markdown validation"""
        errors = []
        warnings = []
        
        try:
            content = filepath.read_text(encoding='utf-8')
            
            # Check for basic structure
            if not content.startswith('---'):
                warnings.append(f"{filepath}: Missing frontmatter")
            
            # Check for empty headings
            if '# ' in content and content.count('# ') < content.count('## '):
                warnings.append(f"{filepath}: More H2 than H1 headings")
            
            # Check for very long lines
            for i, line in enumerate(content.split('\n'), 1):
                if len(line) > 120:
                    warnings.append(f"{filepath}: Line {i} exceeds 120 chars")
            
            # Check for broken markdown links
            import re
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
            for text, url in links:
                if not url or url.isspace():
                    errors.append(f"{filepath}: Empty link URL for '{text}'")
                    
        except Exception as e:
            errors.append(f"{filepath}: Markdown validation error - {e}")
        
        return {'errors': errors, 'warnings': warnings}

    def _validate_json(self, filepath: Path) -> Dict[str, List[str]]:
        """Validate JSON syntax"""
        errors = []
        warnings = []
        
        try:
            content = filepath.read_text(encoding='utf-8')
            import json
            json.loads(content)
        except json.JSONDecodeError as e:
            errors.append(f"{filepath}: Invalid JSON - {e}")
        except Exception as e:
            errors.append(f"{filepath}: JSON validation error - {e}")
        
        return {'errors': errors, 'warnings': warnings}

    def _validate_image(self, filepath: Path) -> Dict[str, List[str]]:
        """Check image optimization"""
        errors = []
        warnings = []
        
        try:
            size = filepath.stat().st_size
            if size > 500 * 1024:  # 500KB
                warnings.append(f"{filepath}: Large image ({size/1024:.0f}KB), consider optimization")
        except Exception as e:
            errors.append(f"{filepath}: Image validation error - {e}")
        
        return {'errors': errors, 'warnings': warnings}

    def _validate_frontmatter(self, filepath: Path) -> Dict[str, List[str]]:
        """Validate YAML frontmatter in markdown files"""
        errors = []
        warnings = []
        
        try:
            content = filepath.read_text(encoding='utf-8')
            if content.startswith('---'):
                # Find the closing ---
                end_idx = content.find('---', 3)
                if end_idx == -1:
                    errors.append(f"{filepath}: Unclosed frontmatter")
                else:
                    frontmatter = content[3:end_idx].strip()
                    import yaml
                    try:
                        yaml.safe_load(frontmatter)
                    except yaml.YAMLError as e:
                        errors.append(f"{filepath}: Invalid YAML frontmatter - {e}")
        except Exception as e:
            errors.append(f"{filepath}: Frontmatter validation error - {e}")
        
        return {'errors': errors, 'warnings': warnings}

    def _stage_files(self, files: List[str]) -> Dict[str, Any]:
        """Stage files for commit"""
        try:
            result = subprocess.run(
                ['git', 'add'] + files,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return {'success': True}
            else:
                return {'success': False, 'errors': [result.stderr]}
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def _generate_commit_message(self, files: List[str]) -> str:
        """Generate conventional commit message"""
        # Categorize files
        categories = {
            'feat(seo)': 0,
            'feat(blog)': 0,
            'fix(metadata)': 0,
            'fix(schema)': 0,
            'docs(seo)': 0,
            'refactor(seo)': 0,
            'chore(seo)': 0
        }
        
        for f in files:
            if 'content/' in f and f.endswith('.md'):
                categories['feat(blog)'] += 1
            elif f.endswith('.json') and 'schema' in f:
                categories['fix(schema)'] += 1
            elif f.endswith('.json') and 'metadata' in f:
                categories['fix(metadata)'] += 1
            elif f.endswith('.md') and 'research/' in f:
                categories['docs(seo)'] += 1
            elif 'refactor' in f:
                categories['refactor(seo)'] += 1
            else:
                categories['chore(seo)'] += 1
        
        # Pick the most common category
        primary = max(categories, key=categories.get)
        count = sum(1 for c in categories.values() if c > 0)
        
        if count == 1:
            msg = f"{primary}: update {len(files)} file"
        else:
            msg = f"{primary}: update {len(files)} files"
        
        if len(files) > 1:
            msg += f" ({', '.join(primary for primary, cnt in categories.items() if cnt > 0)})"
        
        return msg

    def _commit(self, message: str) -> Dict[str, Any]:
        """Commit staged changes"""
        try:
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                # Extract commit hash
                hash_result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                commit_hash = hash_result.stdout.strip()[:8] if hash_result.returncode == 0 else ''
                return {'success': True, 'commit_hash': commit_hash}
            else:
                return {'success': False, 'errors': [result.stderr]}
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def _push(self) -> Dict[str, Any]:
        """Push to remote"""
        try:
            result = subprocess.run(
                ['git', 'push', 'origin', 'HEAD'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {'success': result.returncode == 0, 'pushed': result.returncode == 0}
        except Exception as e:
            return {'success': False, 'pushed': False, 'errors': [str(e)]}

    def _generate_pr_info(self, files: List[str], commit_msg: str) -> Dict[str, Any]:
        """Generate PR information"""
        return {
            'title': commit_msg,
            'body': f"Automated SEO deployment\n\nFiles changed: {len(files)}\n\n" + '\n'.join(f"- {f}" for f in files[:20]),
            'pr_url': f"https://github.com/{self.repo}/pull/new/{self.branch}",
            'branch': self.branch
        }

    def _generate_report(self, files: List[str], validation: Dict, commit_result: Dict, push_result: Dict, pr_info: Dict) -> str:
        """Generate deployment report"""
        report = f"""# Deployment Report

**Deployed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Commit:** {commit_result.get('commit_hash', 'N/A')}
**Message:** {commit_result.get('commit_hash', 'N/A')[:50]}

---

## Files Changed ({len(files)})

"""
        for f in files:
            report += f"- {f}\n"
        
        report += f"""
---

## Validation Results

- **Valid:** {'✅' if validation['valid'] else '❌'}
- **Errors:** {len(validation['errors'])}
- **Warnings:** {len(validation['warnings'])}
- **Files Checked:** {validation['files_checked']}

"""
        if validation['errors']:
            report += "### Errors\n"
            for e in validation['errors']:
                report += f"- {e}\n"
        
        if validation['warnings']:
            report += "\n### Warnings\n"
            for w in validation['warnings']:
                report += f"- {w}\n"
        
        report += f"""
---

## Git Operations

- **Staged:** ✅
- **Committed:** ✅ ({commit_result.get('commit_hash', 'N/A')})
- **Pushed:** {'✅' if push_result.get('pushed') else '⏭️ Skipped'}

---

## Pull Request

- **Title:** {pr_info['title']}
- **Branch:** {pr_info['branch']}
- **URL:** {pr_info['pr_url']}

---
*Generated by GoRentals GitHub Deployment Agent*
"""
        return report