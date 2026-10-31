from locust import HttpUser,task,between

class ProjectUser(HttpUser):
    wait_time=between(1, 3)

    @task(3)
    def view_homePage(self):
        self.client.get("/")
