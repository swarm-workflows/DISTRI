import simpy
import pandas as pd
import itertools  # To generate unique IDs

class ResourcePool:
    # Class-level shared job pool and priority pool (global level)
    common_priority_pool = {}
    common_pool = {}
    common_ledger = {}
    common_working_pool = {}
    common_job_interruption_record = pd.DataFrame(columns=['job_id', 'fault_identification_time', 'processor_id'])  # Global job interruption record
    
    # Class-level ID generator for unique ResourcePool IDs
    _id_counter = itertools.count(0)  # This counter should correctly increment across all instances


    def __init__(self, env, num_categories):
        self.env = env
        self.resource_pool_id = next(ResourcePool._id_counter)  # Assign a unique ID to the ResourcePool instance
        print(f"ResourcePool {self.resource_pool_id} initialized")

        # Initialize instance-specific pools (site-specific)
        self.site_priority_pool = {i: simpy.Store(env) for i in range(num_categories)}
        self.site_pool = {i: simpy.Store(env) for i in range(num_categories)}
        self.site_ledger = {i: [] for i in range(num_categories)}
        self.site_working_pool = {i: [] for i in range(num_categories)}
        
        # Initialize class-level pools if they don't exist (global level)
        if not ResourcePool.common_priority_pool:
            ResourcePool.common_priority_pool = {i: simpy.Store(env) for i in range(num_categories)}
        if not ResourcePool.common_pool:
            ResourcePool.common_pool = {i: simpy.Store(env) for i in range(num_categories)}
        if not ResourcePool.common_ledger:
            ResourcePool.common_ledger = {i: [] for i in range(num_categories)}
        if not ResourcePool.common_working_pool:
            ResourcePool.common_working_pool = {i: [] for i in range(num_categories)}

        # Instance-specific attributes (site-specific)
        self.heartbeat = pd.DataFrame(columns=['processor_id', 'timestamp', 'processor'])  # Heartbeat dataframe
        self.time_series = {i: {'times': [], 'waiting_times': [], 'completion_times': []} for i in range(num_categories)}
        self.processor_fault_record = pd.DataFrame(columns=['processor_id', 'time'])  # Fault record dataframe
        self.fault_check_interval = 1  # Interval to check for faults
        self.env.process(self.fault_checker())  # Start the fault checker process

    def add_job(self, job, priority=False):
        """Add a job to both the site-specific and global priority or standard pool and ledger."""
        # Add to site-specific pool
        pool = self.site_priority_pool if priority else self.site_pool
        pool[job.category].put(job)

        # Add to global pool
        global_pool = ResourcePool.common_priority_pool if priority else ResourcePool.common_pool
        global_pool[job.category].put(job)

        # Record the job in both site-specific and global ledger
        ledger_entry = {
            'job_id': job.id,
            'site_id': None,  
            'processor_id': None,
            'assignment_time': None,
            'reassignment_time': None,
            'completion_time': None,
            'waiting_time': None,
            'creation_time': self.env.now
        }
        self.site_ledger[job.category].append(ledger_entry)
        ResourcePool.common_ledger[job.category].append(ledger_entry)
        
        print(f"ResourcePool {self.resource_pool_id}: added a new job with Job {job.id} to both site and global job pool.")

    def sync_with_global_pools(self, category):
        """Sync the local pools with the global pools by copying jobs from the global to local pools."""
        # Clear the local pools for the specific category
        self.site_priority_pool[category].items.clear()
        self.site_pool[category].items.clear()

        # Copy jobs from the global priority pool to the local priority pool
        for job in ResourcePool.common_priority_pool[category].items:
            self.site_priority_pool[category].put(job)

        # Copy jobs from the global pool to the local pool
        for job in ResourcePool.common_pool[category].items:
            self.site_pool[category].put(job)

        print(f"ResourcePool {self.resource_pool_id}: Synced local pools with global pools for category {category}.")


    def assign_job(self, category, processor_id, processor):
        """Assign a job directly from the global pools to a processor and remove it."""

        # First, synchronize local pools with global pools
        #self.sync_with_global_pools(category)
        
        job = None
        now = self.env.now

        # Check the global priority pool first, as priority jobs should be assigned first
        if len(ResourcePool.common_priority_pool[category].items) > 0:
            job = yield ResourcePool.common_priority_pool[category].get()

        # If no job in priority pool, check the global standard pool
        elif len(ResourcePool.common_pool[category].items) > 0:
            job = yield ResourcePool.common_pool[category].get()

        if job:
            # Job was found in the global pool; now record assignment
            print(f"ResourcePool {self.resource_pool_id}: Job {job.id} fetched from global pool for category {category}.")

            # Remove job from the global pools
            if job in ResourcePool.common_priority_pool[category].items:
                ResourcePool.common_priority_pool[category].items.remove(job)
            elif job in ResourcePool.common_pool[category].items:
                ResourcePool.common_pool[category].items.remove(job)
                
            # Add the job to the global and local working pool
            self.site_working_pool[category].append(job)
            ResourcePool.common_working_pool[category].append(job)

            # Update the global and local ledgers (Update instead of append)
            for record in ResourcePool.common_ledger[category]:
                if record['job_id'] == job.id:
                    record['site_id'] = self.resource_pool_id
                    record['processor_id'] = processor_id
                    record['assignment_time'] = now
                    record['waiting_time'] = now - job.creation_time
                    break

            # Also update the local ledger
            for record in self.site_ledger[category]:
                if record['job_id'] == job.id:
                    record['site_id'] = self.resource_pool_id
                    record['processor_id'] = processor_id
                    record['assignment_time'] = now
                    record['waiting_time'] = now - job.creation_time
                    break

            # Update time series and heartbeat data
            self.time_series[category]['times'].append(now)
            self.time_series[category]['waiting_times'].append(now - job.creation_time)
            self.update_heartbeat(processor_id, now, processor)

            print(f"ResourcePool {self.resource_pool_id}: Job {job.id} assigned to processor {processor_id}.")
            return job
        else:
            print(f"ResourcePool {self.resource_pool_id}: No jobs available in category {category} to assign.")
            return None
        

    def complete_job(self, job, category, processor):
        """Mark a job as completed in both site-specific and global ledgers and remove it from the working pool."""        
   
        now = self.env.now
        assigned_processor_id = None

        # Update the completion status in both site-specific and global ledgers
        for record in ResourcePool.common_ledger[category]:
            if record['job_id'] == job.id and record['completion_time'] is None:
                assigned_processor_id = record['processor_id']
                record['completion_time'] = now - record['assignment_time']
                self.time_series[category]['completion_times'].append(record['completion_time'])
                break

        # Also update the local ledger
        for record in self.site_ledger[category]:
            if record['job_id'] == job.id and record['completion_time'] is None:
                record['completion_time'] = now - record['assignment_time']
                self.time_series[category]['completion_times'].append(record['completion_time'])
                break

        if assigned_processor_id and assigned_processor_id != processor.processor_id:
            # Stop the job on the assigned processor
            try:
                assigned_processor = self.heartbeat.loc[self.heartbeat['processor_id'] == assigned_processor_id, 'processor'].values[0]
                assigned_processor.stop_job(job.id)
            except IndexError:
                print(f"ResourcePool: Assigned processor {assigned_processor_id} not found in the active processors. Ignoring stop job.")

        # Remove job from site-specific and global working pool
        self.site_working_pool[category] = [t for t in self.site_working_pool[category] if t.id != job.id]
        ResourcePool.common_working_pool[category] = [t for t in ResourcePool.common_working_pool[category] if t.id != job.id]

        print(f"ResourcePool {self.resource_pool_id}: Job {job.id} completed by processor {processor.processor_id}.")



    def update_heartbeat(self, processor_id, current_time, processor):
        """Update the heartbeat entry for the processor in the site-specific heartbeat."""
        if processor_id in self.heartbeat['processor_id'].values:
            self.heartbeat.loc[self.heartbeat['processor_id'] == processor_id, ['timestamp', 'processor']] = [current_time, processor]
        else:
            self.heartbeat = pd.concat([self.heartbeat, pd.DataFrame({'processor_id': [processor_id], 'timestamp': [current_time], 'processor': [processor]})], ignore_index=True)

    # def fault_checker(self):
    #     """Continuously checks the heartbeat to identify faulty processors and reassigns their jobs."""
    #     while True:
    #         current_time = self.env.now
    #         for _, row in self.heartbeat.iterrows():
    #             processor_id = row['processor_id']
    #             last_update_time = row['timestamp']
    #             if current_time - last_update_time > 3:
    #                 print(f"ResourcePool {self.resource_pool_id}: Processor {processor_id} is considered faulty. Reassigning its jobs.")
    #                 # Record the fault in the processor_fault_record
    #                 self.processor_fault_record = pd.concat([self.processor_fault_record, pd.DataFrame({'processor_id': [processor_id], 'time': [last_update_time]})], ignore_index=True)
    #                 # Find jobs assigned to this processor in both site-specific and global ledgers
    #                 for category in self.site_ledger:
    #                     for record in self.site_ledger[category]:
    #                         if record['processor_id'] == processor_id and record['completion_time'] is None:
    #                             job_id = record['job_id']
    #                             job = next((t for t in self.site_working_pool[category] if t.id == job_id), None)
    #                             if job:
    #                                 # Record the job interruption in both global and site-specific records
    #                                 ResourcePool.common_job_interruption_record = pd.concat([ResourcePool.common_job_interruption_record, pd.DataFrame({'job_id': [job_id], 'fault_identification_time': [current_time], 'processor_id': [processor_id]})], ignore_index=True)
    #                                 # Remove job from site-specific and global working pools
    #                                 self.site_working_pool[category] = [t for t in self.site_working_pool[category] if t.id != job_id]
    #                                 ResourcePool.common_working_pool[category] = [t for t in ResourcePool.common_working_pool[category] if t.id != job_id]
    #                                 # Move job to site-specific and global priority pool
    #                                 self.site_priority_pool[category].put(job)
    #                                 ResourcePool.common_priority_pool[category].put(job)
    #                                 print(f"ResourcePool {self.resource_pool_id}: Job {job_id} moved to priority pool for category {category}.")
    #                 # Remove the faulty processor from the site-specific heartbeat
    #                 self.heartbeat = self.heartbeat[self.heartbeat['processor_id'] != processor_id]
    #         yield self.env.timeout(self.fault_check_interval)  # Wait for the next check interval

    def fault_checker(self):
        """Continuously checks the heartbeat to identify faulty processors and reassigns their jobs."""
        while True:
            current_time = self.env.now
            for _, row in self.heartbeat.iterrows():
                processor_id = row['processor_id']
                last_update_time = row['timestamp']
                if current_time - last_update_time > 3:
                    print(f"ResourcePool {self.resource_pool_id}: Processor {processor_id} is considered faulty at time {current_time}. Reassigning its jobs.")

                    # Record the fault in the processor_fault_record
                    self.processor_fault_record = pd.concat([self.processor_fault_record, pd.DataFrame({'processor_id': [processor_id], 'time': [last_update_time]})], ignore_index=True)

                    # Search for jobs assigned to this processor in the global ledger (instead of site-specific ledger)
                    jobs_found = False
                    for category, records in ResourcePool.common_ledger.items():
                        print(f"Checking category {category} for jobs assigned to Processor {processor_id}.")
                        for record in records:
                            if record['processor_id'] == processor_id and record['completion_time'] is None:
                                job_id = record['job_id']
                                jobs_found = True
                                print(f"Found job {job_id} assigned to Processor {processor_id}.")

                                
                                # Look for the job in the global working pool
                                job = next((t for t in ResourcePool.common_working_pool[category] if t.id == job_id), None)
                                
                                if job:
                                    # Record job interruption
                                    ResourcePool.common_job_interruption_record = pd.concat(
                                        [ResourcePool.common_job_interruption_record, 
                                        pd.DataFrame({'job_id': [job_id], 'fault_identification_time': [current_time], 'processor_id': [processor_id]})], 
                                        ignore_index=True
                                    )
                                    
                                    # Debug: Job identified
                                    print(f"ResourcePool {self.resource_pool_id}: Found Job {job_id} in global working pool, moving to priority pool.")

                                    # Remove job from both site-specific and global working pools
                                    self.site_working_pool[category] = [t for t in self.site_working_pool[category] if t.id != job_id]
                                    ResourcePool.common_working_pool[category] = [t for t in ResourcePool.common_working_pool[category] if t.id != job_id]

                                    # Move job to both site-specific and global priority pool
                                    self.site_priority_pool[category].put(job)
                                    ResourcePool.common_priority_pool[category].put(job)
                                    print(f"ResourcePool {self.resource_pool_id}: Job {job_id} moved to priority pool for category {category}.")
                                else:
                                    # Debug: Job not found
                                    print(f"ResourcePool {self.resource_pool_id}: Job {job_id} not found in global working pool.")

                    if not jobs_found:
                        print(f"ResourcePool {self.resource_pool_id}: No jobs found assigned to Processor {processor_id}.")

                    # Remove the faulty processor from the site-specific heartbeat
                    self.heartbeat = self.heartbeat[self.heartbeat['processor_id'] != processor_id]
                    print(f"ResourcePool {self.resource_pool_id}: Processor {processor_id} removed from heartbeat.")

            yield self.env.timeout(self.fault_check_interval)  # Wait for the next check interval
