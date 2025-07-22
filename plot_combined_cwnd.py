#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_combined_cwnd():
    """Plot both TCP connections' CWND behavior on the same chart."""
    
    # Read the combined data
    df = pd.read_csv('combined_cwnd_both_connections.csv')
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    # Plot Job 0 (Connection 89696)
    job0_data = df[df['job'] == 'Job0']
    plt.plot(job0_data['time'], job0_data['cwnd'], 
             label='Job 0 (Site 2→Site 0, Conn 89696)', 
             linewidth=2, color='blue', marker='o', markersize=2)
    
    # Plot Job 1 (Connection 98080)
    job1_data = df[df['job'] == 'Job1']
    plt.plot(job1_data['time'], job1_data['cwnd'], 
             label='Job 1 (Site 3→Site 1, Conn 98080)', 
             linewidth=2, color='red', marker='s', markersize=2)
    
    # Customize the plot
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('CWND (Congestion Window)', fontsize=12)
    plt.title('TCP CWND Comparison: Simultaneous Jobs in Dumbell Topology\n(Both connections compete fairly through bottleneck)', fontsize=14, pad=20)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    
    # Add annotations for key phases
    plt.annotate('Slow Start Phase', xy=(2.5, 15), xytext=(3.5, 25),
                arrowprops=dict(arrowstyle='->', color='green'),
                fontsize=10, color='green')
    
    plt.annotate('Congestion Avoidance', xy=(4.5, 65), xytext=(3.8, 55),
                arrowprops=dict(arrowstyle='->', color='purple'),
                fontsize=10, color='purple')
    
    # Set axis limits for better visualization
    plt.xlim(1.5, 5.2)
    plt.ylim(0, 75)
    
    # Create output directory if it doesn't exist
    output_dir = 'runs/42/Combined_Analysis'
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the plot
    plot_path = os.path.join(output_dir, 'combined_cwnd_both_jobs.png')
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"Combined CWND plot saved to: {plot_path}")
    
    # Also save to main directory for easy access
    main_plot_path = 'combined_cwnd_both_jobs.png'
    plt.savefig(main_plot_path, dpi=300, bbox_inches='tight')
    print(f"Combined CWND plot also saved to: {os.path.abspath(main_plot_path)}")
    
    # Move the CSV to the analysis directory too
    import shutil
    csv_dest = os.path.join(output_dir, 'combined_cwnd_both_connections.csv')
    shutil.copy('combined_cwnd_both_connections.csv', csv_dest)
    print(f"Combined CSV copied to: {csv_dest}")
    
    plt.show()
    
    # Print summary statistics
    print("\n=== CWND SUMMARY STATISTICS ===")
    for job in ['Job0', 'Job1']:
        job_data = df[df['job'] == job]
        print(f"\n{job}:")
        print(f"  Start CWND: {job_data['cwnd'].iloc[0]:.1f}")
        print(f"  Max CWND: {job_data['cwnd'].max():.1f}")
        print(f"  Final CWND: {job_data['cwnd'].iloc[-1]:.1f}")
        print(f"  Duration: {job_data['time'].iloc[-1] - job_data['time'].iloc[0]:.2f} seconds")

if __name__ == "__main__":
    plot_combined_cwnd() 