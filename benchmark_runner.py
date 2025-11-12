#!/usr/bin/env python3
"""
Master Benchmark Runner - Chạy tất cả các benchmark và tạo báo cáo tổng hợp
"""

import asyncio
import subprocess
import sys
import time
from datetime import datetime
import os

class BenchmarkRunner:
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.output_dir = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def create_output_dir(self):
        """Tạo thư mục lưu kết quả"""
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"📁 Tạo thư mục kết quả: {self.output_dir}")
        
    def run_benchmark(self, name, script, description):
        """Chạy 1 benchmark script"""
        print(f"\n{'='*70}")
        print(f"🚀 RUNNING: {name}")
        print(f"{'='*70}")
        print(f"📝 Description: {description}")
        print(f"📄 Script: {script}")
        print(f"{'='*70}\n")
        
        start = time.time()
        
        try:
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            duration = time.time() - start
            
            # Save output
            output_file = os.path.join(self.output_dir, f"{name.lower().replace(' ', '_')}.log")
            with open(output_file, 'w') as f:
                f.write(f"=== STDOUT ===\n{result.stdout}\n")
                f.write(f"\n=== STDERR ===\n{result.stderr}\n")
            
            success = result.returncode == 0
            
            self.results[name] = {
                'success': success,
                'duration': duration,
                'output_file': output_file,
                'returncode': result.returncode
            }
            
            if success:
                print(f"\n✅ {name} completed successfully in {duration:.1f}s")
            else:
                print(f"\n❌ {name} failed with return code {result.returncode}")
                print(f"Error output: {result.stderr[:500]}")
            
            # Move generated images to output dir
            for ext in ['.png', '.html', '.csv']:
                for file in os.listdir('.'):
                    if file.endswith(ext) and os.path.isfile(file):
                        new_path = os.path.join(self.output_dir, file)
                        os.rename(file, new_path)
                        print(f"📊 Moved {file} to {self.output_dir}/")
            
            return success
            
        except subprocess.TimeoutExpired:
            print(f"\n⏱️ {name} timed out after 1 hour")
            self.results[name] = {
                'success': False,
                'duration': 3600,
                'output_file': None,
                'returncode': -1,
                'error': 'Timeout'
            }
            return False
            
        except Exception as e:
            print(f"\n❌ Error running {name}: {e}")
            self.results[name] = {
                'success': False,
                'duration': time.time() - start,
                'output_file': None,
                'returncode': -1,
                'error': str(e)
            }
            return False
    
    def generate_summary_report(self):
        """Tạo báo cáo tổng kết"""
        report_file = os.path.join(self.output_dir, "SUMMARY_REPORT.md")
        
        with open(report_file, 'w') as f:
            f.write("# Cassandra Benchmark Summary Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Duration:** {time.time() - self.start_time:.1f} seconds\n\n")
            
            f.write("## Results Overview\n\n")
            f.write("| Benchmark | Status | Duration | Output |\n")
            f.write("|-----------|--------|----------|--------|\n")
            
            total_success = 0
            total_failed = 0
            
            for name, result in self.results.items():
                status = "✅ PASS" if result['success'] else "❌ FAIL"
                duration = f"{result['duration']:.1f}s"
                output = result.get('output_file', 'N/A')
                
                if result['success']:
                    total_success += 1
                else:
                    total_failed += 1
                
                f.write(f"| {name} | {status} | {duration} | {output} |\n")
            
            f.write(f"\n**Total:** {total_success} passed, {total_failed} failed\n\n")
            
            f.write("## Benchmark Details\n\n")
            
            for name, result in self.results.items():
                f.write(f"### {name}\n\n")
                f.write(f"- **Status:** {'✅ PASSED' if result['success'] else '❌ FAILED'}\n")
                f.write(f"- **Duration:** {result['duration']:.2f} seconds\n")
                f.write(f"- **Return Code:** {result['returncode']}\n")
                
                if not result['success'] and 'error' in result:
                    f.write(f"- **Error:** {result['error']}\n")
                
                f.write("\n")
            
            f.write("## Files Generated\n\n")
            files = os.listdir(self.output_dir)
            for file in sorted(files):
                f.write(f"- `{file}`\n")
            
            f.write("\n---\n")
            f.write("*Generated by benchmark_runner.py*\n")
        
        print(f"\n📄 Summary report saved: {report_file}")
        return report_file
    
    def print_final_summary(self):
        """In tóm tắt cuối cùng"""
        print(f"\n{'='*70}")
        print("🎉 ALL BENCHMARKS COMPLETED")
        print(f"{'='*70}\n")
        
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r['success'])
        failed = total - passed
        
        print(f"📊 Results: {passed}/{total} passed, {failed}/{total} failed")
        print(f"⏱️  Total time: {time.time() - self.start_time:.1f} seconds")
        print(f"📁 Output directory: {self.output_dir}")
        print()
        
        for name, result in self.results.items():
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {name}: {result['duration']:.1f}s")
        
        print(f"\n{'='*70}\n")

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║          CASSANDRA BENCHMARK SUITE - MASTER RUNNER                ║
║                                                                   ║
║  This script will run all benchmarks sequentially:                ║
║    1. Basic Benchmark (10k ops)                                   ║
║    2. Consistency Level Comparison (ONE/QUORUM/ALL)               ║
║    3. Fault Tolerance Test (with node failure)                    ║
║    4. Extreme Load Test (1M messages)                             ║
║                                                                   ║
║  ⚠️  WARNING:                                                     ║
║    - Total runtime: 30-60 minutes                                 ║
║    - Will stop/restart Cassandra nodes                            ║
║    - High CPU/RAM/Disk usage                                      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    response = input("\n⚡ Do you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    runner = BenchmarkRunner()
    runner.create_output_dir()
    runner.start_time = time.time()
    
    # Define benchmarks
    benchmarks = [
        {
            'name': 'Basic Benchmark',
            'script': 'benchmark.py',
            'description': 'Standard write/read performance test (10k operations)'
        },
        {
            'name': 'Consistency Level Test',
            'script': 'benchmark_consistency.py',
            'description': 'Compare ONE vs QUORUM vs ALL consistency levels'
        },
        {
            'name': 'Fault Tolerance Test',
            'script': 'benchmark_fault_tolerance.py',
            'description': 'Test behavior when 1 node fails during operation'
        },
        {
            'name': 'Extreme Load Test',
            'script': 'benchmark_extreme_load.py',
            'description': '1 million messages spike test (takes 10-30 min)'
        }
    ]
    
    # Run all benchmarks
    for i, benchmark in enumerate(benchmarks, 1):
        print(f"\n{'#'*70}")
        print(f"# BENCHMARK {i}/{len(benchmarks)}")
        print(f"{'#'*70}")
        
        runner.run_benchmark(
            benchmark['name'],
            benchmark['script'],
            benchmark['description']
        )
        
        # Pause between tests
        if i < len(benchmarks):
            print(f"\n⏸️  Pausing 10 seconds before next test...")
            time.sleep(10)
    
    # Generate report
    runner.generate_summary_report()
    
    # Print summary
    runner.print_final_summary()
    
    print(f"✅ All done! Check {runner.output_dir}/ for detailed results.\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
