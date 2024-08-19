import simpy
import pandas as pd

class ResourcePool:
    def __init__(self, env, num_categories):
        self.env = env
        self.priority_pool = {i: simpy.Store(env) for i in range(num_categories)}  # Priority pools for each category
        self.pools = {i: simpy.Store(env) for i in range(num_categories)}  # Regular pools for each category
        self.working_pool = {i: [] for i in range(num_categories)}  # Working pools for each category
        self.heartbeat = pd.DataFrame(columns=['processor_id', 'timestamp', 'processor'])  # Heartbeat dataframe
        self.ledger = {i: [] for i in range(num_categories)}  # Ledger for each category
        self.time_series = {i: {'times': [], 'waiting_times': [], 'completion_times': []} for i in range(num_categories)}
        self.processor_fault_record = pd.DataFrame(columns=['processor_id', 'time'])  # Fault record dataframe
        self.task_interruption_record = pd.DataFrame(columns=['task_id', 'fault_identification_time', 'processor_id'])  # Task interruption record dataframe
        self.fault_check_interval = 1  # Gradual interval to check for faults
        self.env.process(self.fault_checker())  # Start the fault checker process

    def add_task(self, task, priority=False):
        """Add a task to the appropriate priority or standard pool and ledger entry for tracking."""
        pool = self.priority_pool if priority else self.pools
        pool[task.category].put(task)
        # Record the task with initial values for processor and times in the ledger of the correct category
        self.ledger[task.category].append({
            'task_id': task.id,
            'processor_id': None,
            'assignment_time': None,
            'reassignment_time': None,
            'completion_time': None,
            'waiting_time': None,
            'creation_time': self.env.now
        })    

    def assign_task(self, category, processor_id, processor):
        """Assign a task to a processor and record the time and processor in the ledger."""
        # print(f"ResourcePool: Assigning task from category {category}.")
        task = None
        now = self.env.now
        if self.priority_pool[category].items:
            task = yield self.priority_pool[category].get()
            # Update the ledger with reassignment details
            for record in self.ledger[category]:
                if record['task_id'] == task.id:
                    record['processor_id'] = processor_id
                    record['reassignment_time'] = now
                    print(f"ResourcePool: Task {task.id} reassigned to processor {processor_id}.")
                    break
        elif self.pools[category].items:
            task = yield self.pools[category].get()
            # Update the ledger with assignment details
            for record in self.ledger[category]:
                if record['task_id'] == task.id and record['processor_id'] is None:
                    record['processor_id'] = processor_id
                    record['assignment_time'] = now
                    record['waiting_time'] = now - record['creation_time']
                    self.time_series[category]['times'].append(now)
                    self.time_series[category]['waiting_times'].append(record['waiting_time'])
                    print(f"ResourcePool: Task {task.id} assigned to processor {processor_id}.")
                    break

        # Update heartbeat
        self.update_heartbeat(processor_id, now, processor)

        if task:
            # Add task to working pool
            self.working_pool[category].append(task)
            return task
        else:
            print(f"ResourcePool: No tasks available in category {category} to assign.")
            return None  # Indicate no task available

    def complete_task(self, task, category, processor):
        """Mark a task as completed in the ledger and remove it from the working pool."""
        now = self.env.now
        assigned_processor_id = None
        for record in self.ledger[category]:
            if record['task_id'] == task.id and record['completion_time'] is None:
                assigned_processor_id = record['processor_id']
                record['completion_time'] = now - record['assignment_time']
                self.time_series[category]['completion_times'].append(record['completion_time'])
                break
        if assigned_processor_id and assigned_processor_id != processor.processor_id:
            # Stop the task on the assigned processor
            try:
                assigned_processor = self.heartbeat.loc[self.heartbeat['processor_id'] == assigned_processor_id, 'processor'].values[0]
                assigned_processor.stop_task(task.id)
            except IndexError:
                print(f"ResourcePool: Assigned processor {assigned_processor_id} not found in the active processors. Ignoring stop task.")
        # Remove task from working pool
        self.working_pool[category] = [t for t in self.working_pool[category] if t.id != task.id]

    def update_heartbeat(self, processor_id, current_time, processor):
        """Update the heartbeat entry for the processor with the current timestamp."""
        if processor_id in self.heartbeat['processor_id'].values:
            self.heartbeat.loc[self.heartbeat['processor_id'] == processor_id, ['timestamp', 'processor']] = [current_time, processor]
        else:
            self.heartbeat = pd.concat([self.heartbeat, pd.DataFrame({'processor_id': [processor_id], 'timestamp': [current_time], 'processor': [processor]})], ignore_index=True)

    def fault_checker(self):
        """Continuously checks the heartbeat to identify faulty processors and reassigns their tasks."""
        while True:
            current_time = self.env.now
            for _, row in self.heartbeat.iterrows():
                processor_id = row['processor_id']
                last_update_time = row['timestamp']
                if current_time - last_update_time > 3:
                    print(f"ResourcePool: Processor {processor_id} is considered faulty. Reassigning its tasks.")
                    # Record the fault in the processor_fault_record
                    self.processor_fault_record = pd.concat([self.processor_fault_record, pd.DataFrame({'processor_id': [processor_id], 'time': [last_update_time]})], ignore_index=True)
                    # Find tasks assigned to this processor in the ledger
                    for category in self.ledger:
                        for record in self.ledger[category]:
                            if record['processor_id'] == processor_id and record['completion_time'] is None:
                                task_id = record['task_id']
                                task = next((t for t in self.working_pool[category] if t.id == task_id), None)
                                if task:
                                    # Record the task interruption
                                    self.task_interruption_record = pd.concat([self.task_interruption_record, pd.DataFrame({'task_id': [task_id], 'fault_identification_time': [current_time], 'processor_id': [processor_id]})], ignore_index=True)
                                    # Remove task from working pool
                                    self.working_pool[category] = [t for t in self.working_pool[category] if t.id != task_id]
                                    # Move task to priority pool
                                    self.priority_pool[category].put(task)
                                    print(f"ResourcePool: Task {task_id} moved to priority pool for category {category}.")
                    # Remove the faulty processor from the heartbeat
                    self.heartbeat = self.heartbeat[self.heartbeat['processor_id'] != processor_id]
            yield self.env.timeout(self.fault_check_interval)  # Wait for the next check interval
