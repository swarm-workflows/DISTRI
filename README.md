# DISTRI: Distributed Multi-Facility HPC Simulator

**DISTRI** is an advanced network simulator designed for multi-facility computational infrastructures with **agentic behavior**. It simulates HPC facilities where computational resources act as autonomous agents, making intelligent decisions about job scheduling, load balancing, and resource allocation. The simulator focuses on developing and testing decentralized algorithms that promote resilience and efficiency in multi-facility environments.

## 🎯 **Key Features**

- **🤖 Agentic Resource Behavior**: Processors and DTNs act as autonomous agents with decision-making capabilities
- **🔄 Pheromone-Based Load Balancing**: Decentralized load balancing inspired by ant colony optimization
- **🌐 Dual Topology Support**: Mesh (normal operations) and Dumbell (network testing) topologies
- **📊 Comprehensive TCP Simulation**: Realistic TCP implementations with multiple congestion control algorithms
- **⚡ Failure Resilience Testing**: Processor failure simulation with automatic job reassignment
- **📈 Extensive Visualization**: Detailed performance analysis and metrics collection
- **🔬 Research-Ready**: Designed for algorithm development and benchmarking

## 🏗️ **Architecture Overview**

### **Agentic Behavior Model**

DISTRI implements a sophisticated agentic architecture where computational resources exhibit autonomous behavior:

#### **Processor Agents**
- **Autonomous Job Management**: Each processor continuously monitors for new jobs
- **Intelligent Load Balancing**: Processors use pheromone-based algorithms to make job acceptance decisions
- **Self-Healing**: Automatic failure detection and recovery mechanisms
- **Resource Awareness**: Processors maintain awareness of their current load and capabilities

#### **DTN Agents (Data Transfer Nodes)**
- **Autonomous Data Management**: DTNs make independent decisions about data generation vs. inter-DTN requests
- **Intelligent Routing**: Dynamic routing decisions based on network conditions
- **Load-Aware Processing**: DTNs adapt their behavior based on current system load

#### **Resource Pool Agents**
- **Global Coordination**: Maintains system-wide job queues and processor states
- **Fault Detection**: Continuous monitoring of processor health with automatic job reassignment
- **Load Distribution**: Intelligent job assignment based on processor capabilities and current load

### **Pheromone-Based Load Balancing**

The simulator implements a decentralized load balancing mechanism inspired by ant colony optimization:

```python
# Processors only accept jobs if they're in the lowest 30% load
def is_eligible_for_job(self):
    threshold = sorted(all_levels)[int(len(all_levels) * 0.3)]
    eligible = self.pheromone_map[self.category][self.processor_id] <= threshold
    return eligible
```

**How it works:**
1. **Pheromone Trails**: Each processor maintains a "pheromone level" representing its current load
2. **Threshold-Based Selection**: Only processors in the lowest 30% load accept new jobs
3. **Dynamic Updates**: Pheromone levels are continuously updated as jobs are assigned and completed
4. **Decentralized Decision Making**: No central coordinator - each processor makes independent decisions

## 🌐 **Network Topologies**

### **Mesh Topology (Default)**
**Purpose**: Simulates realistic multi-site HPC operations

- **Multi-site Architecture**: Configurable number of HPC sites (default: 3)
- **Inter-site Communication**: Edge routers enable cross-site data transfer
- **Natural Load Distribution**: Jobs are distributed across sites based on availability
- **Failure Resilience**: Comprehensive fault injection and recovery testing

**Use Cases:**
- Distributed computing algorithm development
- Multi-site coordination testing
- Load balancing algorithm evaluation
- Failure resilience analysis

### **Dumbell Topology**
**Purpose**: Pure network testing and TCP flow competition

- **Controlled Bottleneck**: Artificial bottleneck for testing TCP algorithms
- **Flow Competition**: Two TCP flows compete for bandwidth through bottleneck
- **Fair Testing**: Simultaneous job generation ensures unbiased comparison
- **Network-Focused**: Strips away complexity to focus on network behavior

**Use Cases:**
- TCP congestion control algorithm comparison
- Network fairness testing
- Bottleneck behavior analysis
- Flow competition studies

## 🚀 **Getting Started**

### **Installation**

1. **Clone the repository**:
```bash
git clone <repository-url>
cd DISTRI-master-everything
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Activate virtual environment** (if using venv):
```bash
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### **Basic Usage**

#### **Mesh Topology (Default)**
```bash
python main.py --topology mesh --num-sites 3 --simulation-time 200
```

#### **Dumbell Topology (Network Testing)**
```bash
python main.py --topology dumbell --simulation-time 200
```

## 🔧 **Configuration Parameters**

### **Network Parameters**

| Parameter | Default | Description | Impact |
|-----------|---------|-------------|---------|
| `--router-nic-speed` | 10000 Mbps | Intra-site router speed | Higher = faster local communication |
| `--edge-router-nic-speed` | 20000 Mbps | Inter-site router speed | Higher = faster cross-site communication |
| `--dtn-nic-speed` | 50000 Mbps | DTN data handling speed | Higher = faster data processing |
| `--link-delay` | 0.0001s | Network propagation delay | Higher = more realistic network latency |
| `--router-queue-size` | 250 packets | Router queue capacity | Higher = more buffering, less packet loss |
| `--edge-router-queue-size` | 500 packets | Edge router queue capacity | Higher = better inter-site performance |

### **Topology-Specific Parameters**

#### **Dumbell Topology**
| Parameter | Default | Description | Impact |
|-----------|---------|-------------|---------|
| `--bottleneck-nic-speed` | 1000 Mbps | Bottleneck router speed | Lower = more congestion, more TCP competition |
| `--bottleneck-queue-size` | 25 packets | Bottleneck queue size | Smaller = more packet drops, more TCP backoff |

#### **Mesh Topology**
| Parameter | Default | Description | Impact |
|-----------|---------|-------------|---------|
| `--num-sites` | 3 | Number of HPC sites | More sites = more complex routing |
| `--processors-per-category` | 3 | Processors per job category | More processors = more load balancing options |

### **Job Generation Parameters**

| Parameter | Default | Description | Impact |
|-----------|---------|-------------|---------|
| `--job-generator` | random | Job generation mode | `random` = dynamic jobs, `replay` = fixed sequence |
| `--simulation-time` | 200s | Total simulation duration | Longer = more data, more realistic behavior |
| `--processor-job-lookup-time` | 0.5s | Job checking interval | Shorter = more responsive, higher overhead |

### **Failure Simulation Parameters**

| Parameter | Default | Description | Impact |
|-----------|---------|-------------|---------|
| `--number-of-failures` | 9 | Total processor failures | More failures = more resilience testing |
| `--max-failure-duration` | 10.0s | Maximum failure duration | Longer = more severe impact |
| `--failure-schedule-file` | None | Custom failure schedule | CSV file with specific failure times |

### **TCP and Network Parameters**

| Parameter | Default | Description | Impact |
|-----------|---------|-------------|---------|
| `--cca` | cubic | Congestion control algorithm | `reno`, `cubic`, `htcp` - different TCP behaviors |
| `--aqm` | fifo | Active Queue Management | `fifo` = simple, `fq` = fair queuing |
| `--dtn-data-request` | True | Inter-DTN data sharing | Enables distributed data management |

## 🎮 **Simulation Scenarios**

### **1. Normal Distributed Computing**
```bash
python main.py --topology mesh --num-sites 3 --job-generator random
```
**Purpose**: Simulates realistic multi-site HPC operations with natural job distribution.

### **2. Failure Resilience Testing**
```bash
python main.py --topology mesh --job-generator replay_with_fault --number-of-failures 15
```
**Purpose**: Tests system resilience under processor failures with automatic job reassignment.

### **3. TCP Algorithm Comparison**
```bash
python main.py --topology dumbell --cca reno
python main.py --topology dumbell --cca cubic
python main.py --topology dumbell --cca htcp
```
**Purpose**: Compares different TCP congestion control algorithms under controlled conditions.

### **4. Load Balancing Analysis**
```bash
python main.py --topology mesh --processors-per-category 5 --simulation-time 500
```
**Purpose**: Analyzes pheromone-based load balancing with more processors.

### **5. Network Bottleneck Testing**
```bash
python main.py --topology dumbell --bottleneck-nic-speed 500 --bottleneck-queue-size 10
```
**Purpose**: Tests TCP behavior under severe network congestion.

### **6. Job Replay Analysis**
```bash
python main.py --topology mesh --job-generator replay --job-replay-log jobs.csv
```
**Purpose**: Replays specific job sequences for reproducible experiments.

## 📊 **Results and Analysis**

### **Output Structure**
```
runs/
├── {run_id}/
│   ├── Global_ResourcePool/          # Global job statistics
│   ├── Site_0/                       # Per-site analysis
│   │   ├── dtn/                      # DTN performance metrics
│   │   ├── processors/               # Processor performance
│   │   ├── ResourcePool/             # Job management statistics
│   │   ├── routers/                  # Router performance
│   │   └── TCP_Metrics/              # TCP connection analysis
│   └── Combined_Analysis/            # Cross-site analysis (dumbell)
```

### **Key Metrics**

#### **Performance Metrics**
- **Job Completion Times**: End-to-end job processing duration
- **Data Arrival Times**: Time for data to reach processors
- **Processor Utilization**: CPU and network resource usage
- **Queue Wait Times**: Router and processor queue delays

#### **Network Metrics**
- **TCP Throughput**: Data transfer rates
- **Congestion Window Evolution**: TCP flow control behavior
- **Packet Loss Rates**: Network reliability indicators
- **RTT (Round Trip Time)**: Network latency measurements

#### **Resilience Metrics**
- **Job Reassignment Times**: Recovery from processor failures
- **System Availability**: Uptime under failure conditions
- **Load Distribution**: Fairness of job allocation

## 🧩 **Codebase Architecture**

### **Core Components**

#### **Entities (`entities/`)**
- **`processor.py`**: Autonomous processor agents with job management
- **`dtn.py`**: Data Transfer Node agents with intelligent data routing
- **`resourcepool.py`**: Global resource coordination and fault detection
- **`job.py`**: Job representation with timing and metadata
- **`packet.py`**: Network packet abstraction
- **`router_fifo.py`**: FIFO queue management
- **`router_fq.py`**: Fair Queue management

#### **Protocols (`protocols/`)**
- **`tcp.py`**: RFC-compliant TCP implementation
- **`reno.py`**: Reno congestion control algorithm
- **`cubic.py`**: CUBIC congestion control algorithm
- **`htcp.py`**: High-speed TCP algorithm

#### **Utilities (`utils/`)**
- **`helpers.py`**: Network creation, job generation, and system setup

#### **Visualization (`visualization/`)**
- **`plotting.py`**: Comprehensive analysis and visualization tools

### **Key Design Patterns**

#### **Agentic Architecture**
- **Autonomous Decision Making**: Each component makes independent decisions
- **Decentralized Coordination**: No central controller
- **Self-Organizing Behavior**: System adapts to changing conditions

#### **Event-Driven Simulation**
- **SimPy Framework**: Discrete event simulation
- **Asynchronous Processing**: Concurrent agent execution
- **Realistic Timing**: Accurate simulation of real-world timing

#### **Modular Design**
- **Pluggable Algorithms**: Easy to add new congestion control or load balancing algorithms
- **Configurable Components**: All parameters are externally configurable
- **Extensible Framework**: Easy to add new agent types or behaviors

## 🎯 **Research Applications**

### **Algorithm Development**
- **Load Balancing Algorithms**: Test new decentralized load balancing strategies
- **TCP Improvements**: Develop and test new congestion control algorithms
- **Fault Tolerance**: Design and evaluate fault recovery mechanisms
- **Resource Allocation**: Optimize multi-site resource utilization

### **Performance Analysis**
- **Scalability Studies**: Test system behavior with varying numbers of sites and processors
- **Network Impact**: Analyze how network conditions affect application performance
- **Failure Impact**: Understand system resilience under various failure scenarios
- **Algorithm Comparison**: Benchmark different approaches under controlled conditions

### **Validation Studies**
- **Reproducible Experiments**: Use fixed seeds and job replay for consistent results
- **Parameter Sensitivity**: Analyze how different parameters affect system behavior
- **Real-world Scenarios**: Model actual HPC environments and workloads

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Memory Issues**
- **Large Simulations**: Reduce `--simulation-time` or `--num-sites`
- **Many Processors**: Reduce `--processors-per-category`

#### **Performance Issues**
- **Slow Simulation**: Increase `--processor-job-lookup-time`
- **Network Congestion**: Adjust router speeds and queue sizes

#### **Visualization Issues**
- **Missing Plots**: Check that simulation completed successfully
- **Empty Results**: Verify job generation and processor assignment

### **Debug Mode**
```bash
# Enable verbose logging
python main.py --topology mesh --simulation-time 50 2>&1 | tee debug.log
```

## 📚 **References and Further Reading**

- **SimPy Documentation**: https://simpy.readthedocs.io/
- **TCP Congestion Control**: RFC 5681, RFC 8312
- **Ant Colony Optimization**: Dorigo, M. (2004). Ant colony optimization
- **Distributed Systems**: Tanenbaum, A. S. (2017). Distributed systems: principles and paradigms

## 🤝 **Contributing**

We welcome contributions to DISTRI! Please see our contributing guidelines for:
- Code style and standards
- Testing requirements
- Documentation standards
- Pull request process

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 **Acknowledgments**

- **SimPy Community**: For the excellent discrete event simulation framework
- **Research Community**: For feedback and contributions to the simulator
- **Open Source**: For the many libraries that make this project possible

---

**DISTRI** - Empowering research in distributed computing through realistic simulation of agentic HPC environments.
