# reporting.py
import matplotlib.pyplot as plt
import pandas as pd
import os
from datetime import datetime


class ExperimentReporter:
    def __init__(self, output_dir="./reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_report(self, experiment, metrics_comparison):
        """Generate a report for the experiment results"""
        report_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{self.output_dir}/{experiment['name']}_{report_time}.html"

        # Convert metrics to DataFrame for easier manipulation
        metrics_df = self._metrics_to_dataframe(metrics_comparison)

        # Generate plots (skipped when there is no numeric data to chart)
        plot_file = None
        if not metrics_df.empty and metrics_df["Change (%)"].notna().any():
            plot_file = f"{self.output_dir}/{experiment['name']}_{report_time}.png"
            self._generate_plots(metrics_df, plot_file, experiment["name"])

        # Create HTML report
        with open(report_file, "w") as f:
            f.write(self._generate_html_report(experiment, metrics_df, plot_file))

        return report_file

    def _metrics_to_dataframe(self, metrics_comparison):
        """Convert metrics comparison to pandas DataFrame"""
        data = []

        for metric, values in metrics_comparison.items():
            data.append(
                {
                    "Metric": metric,
                    "Baseline": values["baseline"],
                    "During Experiment": values["current"],
                    "Change (%)": values["change_percent"],
                }
            )

        return pd.DataFrame(
            data, columns=["Metric", "Baseline", "During Experiment", "Change (%)"]
        )

    def _generate_plots(self, metrics_df, output_file, title):
        """Generate visualization of the metrics"""
        fig, ax = plt.subplots(figsize=(10, 6))

        # Create bar chart of percent changes
        metrics_df.plot(
            x="Metric",
            y="Change (%)",
            kind="bar",
            ax=ax,
            title=f"Impact of Chaos Experiment: {title}",
        )

        fig.tight_layout()
        fig.savefig(output_file)
        plt.close(fig)

    def _generate_html_report(self, experiment, metrics_df, plot_file):
        """Generate HTML report with experiment details and results"""
        target = experiment.get("target", {})
        html = f"""
        <html>
        <head>
            <title>Chaos Experiment Report: {experiment["name"]}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ text-align: left; padding: 8px; border: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .summary {{ margin-bottom: 20px; }}
                .metrics {{ margin-top: 20px; }}
                .plot {{ margin-top: 30px; text-align: center; }}
            </style>
        </head>
        <body>
            <h1>Chaos Experiment Report</h1>
            
            <div class="summary">
                <h2>Experiment Summary</h2>
                <p><strong>Name:</strong> {experiment["name"]}</p>
                <p><strong>Type:</strong> {experiment["type"]}</p>
                <p><strong>Description:</strong> {experiment.get("description", "n/a")}</p>
                <p><strong>Duration:</strong> {experiment["duration"]} seconds</p>
                <p><strong>Target Environment:</strong> {target.get("environment", "n/a")}</p>
                <p><strong>Target Service:</strong> {target.get("service", "n/a")}</p>
            </div>
            
            <div class="metrics">
                <h2>Metrics Impact</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Baseline</th>
                        <th>During Experiment</th>
                        <th>Change (%)</th>
                    </tr>
                    {self._generate_table_rows(metrics_df)}
                </table>
            </div>
            
            <div class="plot">
                <h2>Visual Impact</h2>
                {self._generate_plot_html(plot_file)}
            </div>
            
            <div class="conclusion">
                <h2>Conclusion</h2>
                <p>This report provides the results of a chaos engineering experiment designed to test system resilience.</p>
                <p>Success Criteria Results:</p>
                <ul>
                    {self._generate_success_criteria_items(experiment)}
                </ul>
            </div>
        </body>
        </html>
        """
        return html

    def _generate_plot_html(self, plot_file):
        """Generate the plot image tag, or a placeholder when no plot was made"""
        if plot_file is None:
            return "<p>No metric changes to visualize.</p>"
        return f'<img src="{os.path.basename(plot_file)}" alt="Experiment Impact Visualization">'

    def _generate_table_rows(self, metrics_df):
        """Generate HTML table rows for metrics"""
        if metrics_df.empty:
            return '<tr><td colspan="4">No metrics were collected.</td></tr>'

        rows = ""
        for _, row in metrics_df.iterrows():
            change = row["Change (%)"]
            change_text = "n/a" if pd.isna(change) else f"{change:.2f}%"
            rows += f"""
            <tr>
                <td>{row["Metric"]}</td>
                <td>{row["Baseline"]:.2f}</td>
                <td>{row["During Experiment"]:.2f}</td>
                <td>{change_text}</td>
            </tr>
            """
        return rows

    def _generate_success_criteria_items(self, experiment):
        """Generate HTML list items for success criteria"""
        items = ""
        if "success_criteria" in experiment:
            for criterion in experiment["success_criteria"]:
                items += f"<li>{criterion} - <em>Manual verification required</em></li>"
        else:
            items = "<li>No specific success criteria defined</li>"
        return items
