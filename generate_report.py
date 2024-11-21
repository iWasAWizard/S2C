import csv
import matplotlib.pyplot as plt
import argparse
import os
import sys

def generate_report(csv_file, output_html):
    """
    Generates an HTML report with line graphs for each metric.

    Args:
        csv_file (str): The CSV file containing the metrics.
        output_html (str): The output HTML file.
    """
    data = {}
    try:
        with open(csv_file, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                for key, value in row.items():
                    data.setdefault(key, []).append(float(value))
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading '{csv_file}': {e}")
        sys.exit(1)

    metrics = ['Bandwidth(bps)', 'Latency(s)', 'Jitter(s)', 'Packet Loss(%)', 'Corrupt Packets', 'Out-of-Order Packets']
    time = data.get('Time')
    if not time:
        print("Error: 'Time' column not found in the CSV file.")
        sys.exit(1)

    html_content = '<html><head><title>Network Metrics Report</title></head><body>'
    html_content += '<h1>Network Metrics Report</h1>'

    for metric in metrics:
        if metric not in data:
            print(f"Warning: '{metric}' column not found in the CSV file.")
            continue

        plt.figure()
        plt.plot(time, data[metric])
        plt.xlabel('Time (s)')
        plt.ylabel(metric)
        plt.title(f'{metric} over Time')
        img_file = f'{metric.replace("/", "_").replace("(", "").replace(")", "").replace("%", "Percent").replace(" ", "_")}.png'
        plt.savefig(img_file)
        plt.close()

        # Embed the image in HTML
        html_content += f'<h2>{metric} over Time</h2>'
        html_content += f'<img src="{img_file}" alt="{metric} over Time"><br>'

    html_content += '</body></html>'

    try:
        with open(output_html, 'w') as html_file:
            html_file.write(html_content)
        print(f"Report generated: {output_html}")
    except Exception as e:
        print(f"Error writing to '{output_html}': {e}")
        sys.exit(1)

def print_help():
    """
    Prints detailed help information for the report generator script.
    """
    help_text = """
    Network Metrics Report Generator

    Usage:
        python3 report_generator.py [options]

    Options:
        --input_csv FILE       Input CSV file with metrics (required)
        --output_html FILE     Output HTML report file (default: report.html)
        -h, --help             Show this help message and exit

    Examples:
        python3 report_generator.py --input_csv metrics.csv
        python3 report_generator.py --input_csv metrics.csv --output_html custom_report.html
    """
    print(help_text)

if __name__ == '__main__':
    # Check for help flag or no arguments
    if '-h' in sys.argv or '--help' in sys.argv or len(sys.argv) == 1:
        print_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(description='Network Metrics Report Generator', add_help=False)
    parser.add_argument('--input_csv', type=str, required=False, help='Input CSV file with metrics (required)')
    parser.add_argument('--output_html', type=str, default='report.html', help='Output HTML report file (default: report.html)')
    args, unknown = parser.parse_known_args()

    # Check for unrecognized arguments
    if unknown:
        print(f"Unrecognized arguments: {' '.join(unknown)}\n")
        print_help()
        sys.exit(1)

    # Check if input_csv is provided
    if not args.input_csv:
        print("Error: --input_csv is required.\n")
        print_help()
        sys.exit(1)

    generate_report(args.input_csv, args.output_html)