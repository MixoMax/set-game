import requests
import matplotlib.pyplot as plt
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

session = requests.Session()

def fetch_one(n_cards, server_url):
    global session
    cards_response = session.post(f"{server_url}/deal_cards", json={"n_cards": n_cards})
    cards_response.raise_for_status()
    cards_json = cards_response.json()["cards"]

    sets_response = session.post(f"{server_url}/find_all_sets", json=cards_json)
    sets_response.raise_for_status()
    all_sets = sets_response.json()["sets"]
    
    return len(all_sets)

def calculate_frequency(n_cards, n_samples, max_workers, server_url):
    frequency = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_one, n_cards, server_url) for _ in range(n_samples)]
        for future in tqdm(as_completed(futures), total=n_samples):
            n_sets = future.result()
            frequency[n_sets] = frequency.get(n_sets, 0) + 1
    
    return frequency

def main():
    parser = argparse.ArgumentParser(description="Plot binomial distribution of sets in cards.")
    parser.add_argument("--max-workers", type=int, default=50, help="Maximum number of worker threads.")
    parser.add_argument("--start-range", type=int, default=3, help="Start of the range for number of cards.")
    parser.add_argument("--end-range", type=int, default=14, help="End of the range for number of cards (inclusive).")
    parser.add_argument("--n_samples", type=int, default=1000, help="Number of samples to take.")
    parser.add_argument("--server-url", type=str, default="http://127.0.0.1:8000/api/v1", help="URL of the set server.")
    args = parser.parse_args()

    for n_cards in range(args.start_range, args.end_range + 1):
        frequency = calculate_frequency(n_cards, args.n_samples, args.max_workers, args.server_url)

        plt.bar(frequency.keys(), frequency.values())
        plt.xlabel("Number of sets")
        plt.ylabel("Frequency")
        plt.title(f"Distribution of sets in {n_cards} cards ({args.n_samples} samples)")

        for n, freq in frequency.items():
            perc = freq / args.n_samples * 100
            plt.text(n, freq + 0.4, f"{perc:.3f}%", ha='center', va='bottom', fontsize=8)

        plt.xticks(list(frequency.keys()))
        plt.savefig(f"images/binom_{n_cards}_cards.png", dpi=300, bbox_inches='tight')
        plt.clf()

if __name__ == "__main__":
    main()
