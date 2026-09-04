from locust import HttpUser, task, between


class SaaSUser(HttpUser):
    wait_time = between(0.1, 0.5)
    host = "http://localhost:8000"

    def on_start(self):
        response = self.client.post(
            "/auth/login/acme_corp",
            json={
                "email": "admin@acme.com",
                "password": "Admin@123"
            }
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            self.headers = {}

    @task(3)
    def list_users(self):
        self.client.get("/users/", headers=self.headers)

    @task(2)
    def get_my_profile(self):
        self.client.get("/users/me", headers=self.headers)

    @task(1)
    def list_documents(self):
        self.client.get("/documents/", headers=self.headers)

    @task(1)
    def health_check(self):
        self.client.get("/health")