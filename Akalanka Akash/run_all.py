from scripts.analyse import analyse
from scripts.prepare_data import prepare


if __name__ == "__main__":
    prepare()
    results = analyse()
    print("Analysis complete")
    print(f"Welch p-value: {results['welch_two_sample_t_test']['p_value_two_sided']:.4f}")

