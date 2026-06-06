from locust import HttpUser, task, between
import uuid
import json

class BankingUser(HttpUser):
    wait_time = between(0.1, 0.5)
    
    def on_start(self):
        """Load customer credentials from seed file."""
        try:
            with open("scripts/stress_customers.json") as f:
                self.customers = json.load(f)
        except FileNotFoundError:
            print("ERROR: Run scripts/seed_dummy_data.py first!")
            self.customers = []
        
        self.customer = self.customers[self.user_id % len(self.customers)] if self.customers else None
    
    @task(5)
    def transfer(self):
        if not self.customer:
            return
        dst = self.customers[(self.user_id + 1) % len(self.customers)]
        
        self.client.post(
            "/transactions/transfer",
            json={
                "source_account_id": self.customer["account_id"],
                "destination_account_number": dst["account_number"],
                "amount": 10,
                "idempotency_key": f"locust-{self.user_id}-{uuid.uuid4().hex[:8]}"
            },
            headers={"Authorization": f"Bearer {self.customer['token']}"}
        )
    
    @task(3)
    def get_statement(self):
        if not self.customer:
            return
        self.client.get(
            f"/transactions/statement/{self.customer['account_id']}?limit=5",
            headers={"Authorization": f"Bearer {self.customer['token']}"}
        )
    
    @task(2)
    def get_accounts(self):
        if not self.customer:
            return
        self.client.get(
            "/customer/accounts",
            headers={"Authorization": f"Bearer {self.customer['token']}"}
        )
    
    @task(1)
    def get_profile(self):
        if not self.customer:
            return
        self.client.get(
            "/customer/profile",
            headers={"Authorization": f"Bearer {self.customer['token']}"}
        )