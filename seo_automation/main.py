"""
Master Orchestrator for GoRentals 12-Agent SEO Automation System
Runs the complete SEO automation cycle with all 12 agents
Supports daily scheduled runs, continuous mode, and auto GitHub deployment
"""
import asyncio
import json
import sys
import schedule
import time
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse

# FORCE CLEAR ALL AGENT MODULES FROM CACHE BEFORE ANY IMPORTS
# This must happen BEFORE any imports to prevent cached bytecode from loading
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith('agents.'):
        del sys.modules[mod_name]

# Add project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEO_DIR = PROJECT_ROOT / "seo"
SEO_AUTO_DIR = PROJECT_ROOT / "seo_automation"

sys.path.insert(0, str(SEO_AUTO_DIR))
sys.path.insert(0, str(SEO_DIR))

from agents.base import BaseAgent, AgentResult, load_config

# Import Evolution Engine for continuous learning
sys.path.insert(0, str(SEO_DIR / "scripts"))
from self_improving_engine import run_evolution_cycle, load_json, EXPERIMENTS_PATH, LEARNINGS_PATH, STRATEGY_PATH


class MasterOrchestrator:
    """Main orchestrator for the 12-agent SEO automation system"""

    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = load_config(config_path)
        self.project_root = PROJECT_ROOT
        self.seo_dir = SEO_DIR
        self.auto_dir = SEO_AUTO_DIR
        self.results = {}
        self.context = {}
        self.start_time = datetime.now()
        self.running = True

        # Load scheduler and continuous improvement config
        self.scheduler_config = self.config.get('scheduler', {})
        self.continuous_config = self.config.get('continuous_improvement', {})
        self.github_config = self.config.get('agents', {}).get('github_deployment', {})

    def initialize_agents(self) -> Dict[str, BaseAgent]:
        """Initialize all 12 agents - load from source files to bypass cache"""
        import importlib.util
        import sys

        def load_module(module_name: str, file_path: Path):
            """Load module from source file, bypassing import cache"""
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module

        agent_files = {
            'keyword_intelligence': self.auto_dir / 'agents' / 'keyword_intelligence.py',
            'competitor_intelligence': self.auto_dir / 'agents' / 'competitor_intelligence.py',
            'serp_analysis': self.auto_dir / 'agents' / 'serp_analysis.py',
            'content_strategy': self.auto_dir / 'agents' / 'content_strategy.py',
            'seo_writer': self.auto_dir / 'agents' / 'seo_writer.py',
            'technical_seo': self.auto_dir / 'agents' / 'technical_seo.py',
            'internal_linking': self.auto_dir / 'agents' / 'internal_linking.py',
            'local_seo': self.auto_dir / 'agents' / 'local_seo.py',
            'eeat_optimization': self.auto_dir / 'agents' / 'eeat_optimization.py',
            'content_refresh': self.auto_dir / 'agents' / 'content_refresh.py',
            'github_deployment': self.auto_dir / 'agents' / 'github_deployment.py',
            'performance_tracking': self.auto_dir / 'agents' / 'performance_tracking.py'
        }

        agents = {}
        for name, path in agent_files.items():
            if path.exists():
                agents[name] = load_module(f'agents.{name}', path)
            else:
                print(f"Warning: {path} not found")

        agent_instances = {}

        agent_configs = self.config.get('agents', {})

        agent_instances['keyword_intelligence'] = agents['keyword_intelligence'].KeywordIntelligenceAgent(
            'keyword_intelligence', agent_configs.get('keyword_intelligence', {}), self.auto_dir
        )

        agent_instances['competitor_intelligence'] = agents['competitor_intelligence'].CompetitorIntelligenceAgent(
            'competitor_intelligence', agent_configs.get('competitor_intelligence', {}), self.auto_dir
        )

        agent_instances['serp_analysis'] = agents['serp_analysis'].SERPAnalysisAgent(
            'serp_analysis', agent_configs.get('serp_analysis', {}), self.auto_dir
        )

        agent_instances['content_strategy'] = agents['content_strategy'].ContentStrategyAgent(
            'content_strategy', agent_configs.get('content_strategy', {}), self.auto_dir
        )

        agent_instances['seo_writer'] = agents['seo_writer'].SEOContentWriterAgent(
            'seo_writer', agent_configs.get('seo_writer', {}), self.auto_dir
        )

        agent_instances['technical_seo'] = agents['technical_seo'].TechnicalSEOAgent(
            'technical_seo', agent_configs.get('technical_seo', {}), self.auto_dir
        )

        agent_instances['internal_linking'] = agents['internal_linking'].InternalLinkingAgent(
            'internal_linking', agent_configs.get('internal_linking', {}), self.auto_dir
        )

        agent_instances['local_seo'] = agents['local_seo'].LocalSEOAgent(
            'local_seo', agent_configs.get('local_seo', {}), self.auto_dir
        )

        agent_instances['eeat_optimization'] = agents['eeat_optimization'].EEATOptimizationAgent(
            'eeat_optimization', agent_configs.get('eeat_optimization', {}), self.auto_dir
        )

        agent_instances['content_refresh'] = agents['content_refresh'].ContentRefreshAgent(
            'content_refresh', agent_configs.get('content_refresh', {}), self.auto_dir
        )

        agent_instances['github_deployment'] = agents['github_deployment'].GitHubDeploymentAgent(
            'github_deployment', agent_configs.get('github_deployment', {}), self.auto_dir
        )

        agent_instances['performance_tracking'] = agents['performance_tracking'].PerformanceTrackingAgent(
            'performance_tracking', agent_configs.get('performance_tracking', {}), self.auto_dir
        )

        return agent_instances

    def load_context(self) -> Dict[str, Any]:
        """Load existing data as context for agents"""
        context = {
            'keywords': [],
            'clusters': [],
            'content_calendar': [],
            'pages': [],
            'existing_content': [],
            'competitor_data': {},
            'serp_analysis': {},
            'changed_files': [],
            'performance_history': [],
            'learnings': []
        }

        # Load keywords
        kw_file = self.auto_dir / "research" / "keywords.json"
        if kw_file.exists():
            with open(kw_file, 'r') as f:
                data = json.load(f)
                context['keywords'] = data.get('keywords', [])

        # Load clusters
        cluster_file = self.auto_dir / "research" / "keyword_clusters.json"
        if cluster_file.exists():
            with open(cluster_file, 'r') as f:
                data = json.load(f)
                context['clusters'] = data.get('clusters', [])

        # Load content calendar
        cal_file = self.auto_dir / "research" / "content_calendar.json"
        if cal_file.exists():
            with open(cal_file, 'r') as f:
                data = json.load(f)
                context['content_calendar'] = data.get('calendar', [])

        # Load production priorities
        priority_file = self.auto_dir / "research" / "production_priorities.json"
        if priority_file.exists():
            with open(priority_file, 'r') as f:
                data = json.load(f)
                context['prioritized_content'] = data.get('items', [])

        # Load existing content inventory
        drafts_dir = self.seo_dir / "drafts"
        if drafts_dir.exists():
            for md_file in drafts_dir.rglob("*.md"):
                if not md_file.name.startswith('_'):
                    context['existing_content'].append({
                        'url': f"/{md_file.relative_to(self.seo_dir / 'drafts').with_suffix('')}",
                        'title': md_file.stem.replace('-', ' ').title(),
                        'filepath': str(md_file)
                    })

        # Load competitor data
        comp_file = self.auto_dir / "research" / "competitor-analysis.json"
        if comp_file.exists():
            with open(comp_file, 'r') as f:
                context['competitor_data'] = json.load(f)

        # Load SERP analysis
        serp_file = self.auto_dir / "research" / "serp-analysis.md"
        if serp_file.exists():
            context['serp_analysis'] = {'report': serp_file.read_text()}

        # Load performance data
        perf_file = self.auto_dir / "research" / "performance-metrics.json"
        if perf_file.exists():
            with open(perf_file, 'r') as f:
                context['performance'] = json.load(f)

        # Load learnings for continuous improvement
        learnings_file = self.seo_dir / "memory" / "learnings.json"
        if learnings_file.exists():
            with open(learnings_file, 'r') as f:
                context['learnings'] = json.load(f)

        return context

    def run_agent(self, name: str, agent: BaseAgent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single agent with error handling"""
        start = datetime.now()
        print(f"\n============================================================")
        print(f"▶ Running {name}...")
        print(f"============================================================")

        try:
            result = asyncio.run(agent.execute(context))
            duration = (datetime.now() - start).total_seconds()
            success = getattr(result, 'success', True)
            files = getattr(result, 'files_created', [])
            errors = getattr(result, 'errors', [])

            if success:
                print(f"  ✅ {name} completed in {duration:.1f}s")
                for f in files:
                    print(f"    📄 {f}")
            else:
                print(f"  ❌ {name} failed after {duration:.1f}s")
                for e in errors:
                    print(f"    ⚠️  {e}")

            return {
                'agent': name,
                'success': success,
                'data': getattr(result, 'data', {}),
                'errors': errors,
                'files': files,
                'duration': duration
            }

        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            print(f"  ❌ {name} failed after {duration:.1f}s: {e}")
            return {
                'agent': name,
                'success': False,
                'data': {},
                'errors': [str(e)],
                'files': [],
                'duration': duration
            }

    def run_full_cycle(self) -> Dict[str, Any]:
        """Run the complete 12-agent SEO automation cycle"""
        print(f"\n{'='*60}")
        print(f"🚀 GoRentals 12-Agent SEO Automation - FULL MODE")
        print(f"{'='*60}")

        # Initialize agents
        agents = self.initialize_agents()
        print(f"\n📦 Initialized {len(agents)} agents")

        # Load context
        self.context = self.load_context()
        print(f"📚 Loaded context: {len(self.context.get('keywords', []))} keywords, {len(self.context.get('clusters', []))} clusters")

        # Run agents in order
        agent_order = [
            'performance_tracking',
            'keyword_intelligence',
            'competitor_intelligence',
            'serp_analysis',
            'content_strategy',
            'seo_writer',
            'technical_seo',
            'internal_linking',
            'local_seo',
            'eeat_optimization',
            'content_refresh',
            'github_deployment'
        ]

        results = {}
        for name in agent_order:
            agent = agents.get(name)
            if agent:
                self.results[name] = self.run_agent(name, agent, self.context)
            else:
                print(f"  ⚠️  Agent {name} not found, skipping")

        # Continuous improvement cycle
        if self.continuous_config.get('enabled', True):
            print(f"\n============================================================")
            print(f"🔄 CONTINUOUS IMPROVEMENT CYCLE")
            print(f"============================================================")
            try:
                improvements = asyncio.run(run_evolution_cycle(self.context))
                if improvements:
                    print(f"✅ Continuous improvement cycle complete - {len(improvements)} improvements applied")
                    for imp in improvements:
                        print(f"  ✅ {imp}")
            except Exception as e:
                print(f"⚠️  Continuous improvement cycle failed: {e}")

        # Final github deployment (runs twice - once during cycle, once after improvements)
        print(f"\n============================================================")
        print(f"▶ Running github_deployment (final)...")
        print(f"============================================================")
        github_agent = agents.get('github_deployment')
        if github_agent:
            self.run_agent('github_deployment', github_agent, self.context)

        # Summary
        print(f"\n============================================================")
        print(f"📊 EXECUTION SUMMARY")
        print(f"============================================================")

        successful = sum(1 for r in self.results.values() if r['success'])
        failed = len(self.results) - successful
        total_files = sum(len(r.get('files', [])) for r in self.results.values())

        print(f"\n✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"\n📁 Total files generated: {total_files}")

        print(f"\n📋 Agent Results:")
        for name, result in self.results.items():
            status = "✅" if result['success'] else "❌"
            print(f"  {status} {name}: {result['duration']:.1f}s, {len(result.get('files', []))} files")
            for e in result.get('errors', []):
                print(f"    ⚠️  {e}")

        print(f"\n⏱️  Total duration: {(datetime.now() - self.start_time).total_seconds():.1f}s")
        print(f"📁 All outputs in: {self.auto_dir}/")
        print(f"\n============================================================")
        print(f"🎯 CYCLE COMPLETE")
        print(f"============================================================")

        return self.results

    def run_scheduler(self):
        """Run the scheduler for automated daily runs"""
        if not self.scheduler_config.get('enabled', False):
            print("Scheduler not enabled in config")
            return

        schedule_time = self.scheduler_config.get('daily_run_time', '02:00')
        schedule.every().day.at(schedule_time).do(self.run_full_cycle)

        print(f"📅 Scheduler started - running daily at {schedule_time}")
        print("Press Ctrl+C to stop")

        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n🛑 Scheduler stopped")
            self.running = False


def main():
    parser = argparse.ArgumentParser(description='GoRentals 12-Agent SEO Automation')
    parser.add_argument('--mode', choices=['full', 'continuous', 'schedule'], default='full',
                       help='Run mode: full (single cycle), continuous (loop), schedule (daily)')
    parser.add_argument('--config', default='config/settings.yaml', help='Config file path')
    args = parser.parse_args()

    orchestrator = MasterOrchestrator(args.config)

    if args.mode == 'full':
        orchestrator.run_full_cycle()
    elif args.mode == 'continuous':
        while True:
            orchestrator.run_full_cycle()
            delay = orchestrator.continuous_config.get('delay_minutes', 60)
            print(f"\n😴 Sleeping for {delay} minutes...")
            time.sleep(delay * 60)
    elif args.mode == 'schedule':
        orchestrator.run_scheduler()


if __name__ == '__main__':
    main()