"""运行核心测试和安全基准，并汇总验证报告。"""
import json
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = PROJECT_ROOT / 'experiments' / 'security_benchmark_results'
REPORT_PATH = RESULT_DIR / 'validation_report.md'


def run_command(args):
    start = time.time()
    completed = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    elapsed = time.time() - start
    return {
        'args': ' '.join(args),
        'returncode': completed.returncode,
        'elapsed': elapsed,
        'output': completed.stdout
    }


def tail_lines(text, n=60):
    lines = text.strip().splitlines()
    return '\n'.join(lines[-n:])


def load_benchmark_summary():
    path = RESULT_DIR / 'security_benchmark_results.json'
    if not path.exists():
        return None
    with path.open(encoding='utf-8') as f:
        return json.load(f)


def write_report(test_run, benchmark_run):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    benchmark = load_benchmark_summary()

    status = 'PASS' if test_run['returncode'] == 0 and benchmark_run['returncode'] == 0 else 'FAIL'
    lines = [
        '# Full Validation Report',
        '',
        f'- Overall status: {status}',
        f'- Test command: `{test_run["args"]}`',
        f'- Test return code: {test_run["returncode"]}',
        f'- Test elapsed: {test_run["elapsed"]:.2f}s',
        f'- Benchmark command: `{benchmark_run["args"]}`',
        f'- Benchmark return code: {benchmark_run["returncode"]}',
        f'- Benchmark elapsed: {benchmark_run["elapsed"]:.2f}s',
        ''
    ]

    if benchmark:
        qkd = benchmark['qkd']
        qdp_eps1 = next(
            x for x in benchmark['qdp_gradient_inversion']['epsilon_scan']
            if x['epsilon'] == 1.0
        )
        mpo = benchmark['mpo']['adaptive']
        fl = benchmark['federated_learning']
        poison = benchmark['model_poisoning']

        lines.extend([
            '## Benchmark Highlights',
            '',
            f'- QKD Eve detection rate: {qkd["eve_detection_rate"] * 100:.1f}%',
            f'- QKD normal/eavesdropping error: {qkd["normal_avg_error_rate"]:.2f}% / {qkd["eve_avg_error_rate"]:.2f}%',
            f'- QDP epsilon=1 attack success rate: {qdp_eps1["attack_success_rate"] * 100:.1f}%',
            f'- Adaptive MPO communication saving: {mpo["communication_saving_pct"]:.2f}%',
            f'- Five-seed baseline test accuracy: '
            f'{fl["baseline_fedavg"]["final_accuracy"]:.2f}% ± '
            f'{fl["baseline_fedavg"]["final_accuracy_std"]:.2f}%',
            f'- Five-seed proposed test accuracy: '
            f'{fl["secure_qdp_adaptive_mpo"]["final_accuracy"]:.2f}% ± '
            f'{fl["secure_qdp_adaptive_mpo"]["final_accuracy_std"]:.2f}%',
            f'- Proposed vs baseline accuracy delta: '
            f'{fl["secure_qdp_adaptive_mpo"]["final_accuracy"] - fl["baseline_fedavg"]["final_accuracy"]:+.2f}%',
            f'- Proposed/baseline final loss: '
            f'{fl["secure_qdp_adaptive_mpo"]["final_loss"]:.3f} / '
            f'{fl["baseline_fedavg"]["final_loss"]:.3f}',
            f'- Proposed average communication saving: '
            f'{fl["secure_qdp_adaptive_mpo"]["avg_communication_saving_pct"]:.2f}%',
            f'- Validation-only model selection: {fl.get("selection_protocol", {})}',
            f'- Ablation controls: {fl.get("comparison_note", "-")}',
            f'- Median/Krum poisoning reduction: {poison["median_reduction_vs_fedavg"] * 100:.1f}% / {poison["krum_reduction_vs_fedavg"] * 100:.1f}%',
            ''
        ])

    lines.extend([
        '## Test Output Tail',
        '',
        '```text',
        tail_lines(test_run['output']),
        '```',
        '',
        '## Benchmark Output Tail',
        '',
        '```text',
        tail_lines(benchmark_run['output']),
        '```',
        ''
    ])

    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')


def main():
    test_run = run_command([sys.executable, 'tests/test_all_modules.py'])
    benchmark_run = run_command([sys.executable, 'experiments/run_security_benchmark.py'])
    write_report(test_run, benchmark_run)

    print('=' * 70)
    print('  一键完整验证完成')
    print('=' * 70)
    print(f'  测试返回码: {test_run["returncode"]}')
    print(f'  基准返回码: {benchmark_run["returncode"]}')
    print(f'  验证报告: {REPORT_PATH}')
    print('=' * 70)

    return 0 if test_run['returncode'] == 0 and benchmark_run['returncode'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
