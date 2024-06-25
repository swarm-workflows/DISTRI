import simpy

class ResourcePool:
    def __init__(self, env, num_categories):
        self.env = env
        self.pools = {i: simpy.Store(env) for i in range(num_categories)}  # Stores for each category
        self.ledger = {i: [] for i in range(num_categories)}  # Ledger for each category
        self.time_series = {i: {'times': [], 'waiting_times': [], 'completion_times': []} for i in range(num_categories)}

    def add_task(self, task):
        """Add a task to the appropriate category pool and ledger entry for tracking."""
        self.pools[task.category].put(task)
        # Record the task with initial values for processor and times in the ledger of the correct category
        self.ledger[task.category].append({
            'task_id': task.id,
            'processor_id': None,
            'assignment_time': None,
            'completion_time': None,
            'waiting_time': None,
            'creation_time': self.env.now
        })    

    def assign_task(self, category, processor_id):
        """Assign a task to a processor and record the time and processor in the ledger."""
        print(f"ResourcePool: Assigning task from category {category}.")
        if self.pools[category].items:
            task = yield self.pools[category].get()
            now = self.env.now
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
            return task
        else:
            print(f"ResourcePool: No tasks available in category {category} to assign.")
            return None  # Indicate no task available

    def complete_task(self, task, category):
        """Mark a task as completed in the ledger."""
        now = self.env.now
        for record in self.ledger[category]:
            if record['task_id'] == task.id and record['completion_time'] is None:
                record['completion_time'] = now
                record['completion_time'] = now - record['assignment_time']
                self.time_series[category]['completion_times'].append(record['completion_time'])
                break