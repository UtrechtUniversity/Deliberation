from locust import HttpUser, TaskSet, task
from locust.exception import StopUser


class OtreeApplication:

    def __init__(
        self,
        client,
        start_url,
    ):
        self.client = client
        self.start_url = start_url

    def run_experiment(self):


        # 1. Open the oTree room Welcome page


        with self.client.get(
            self.start_url,
            name="Open room",
            catch_response=True,
            allow_redirects=True,
        ) as response:

            if not response.ok:
                response.failure(
                    f"Could not open room: "
                    f"status={response.status_code}, "
                    f"url={response.url}"
                )
                return

            response.success()

   
        # 2. Submit the Welcome page's Start button


        with self.client.post(
            self.start_url,
            json={},
            headers={
                "X-Requested-With": "XMLHttpRequest",
            },
            name="Click Start",
            catch_response=True,
        ) as response:

            try:
                response_data = response.json()
            except ValueError:
                response.failure(
                    f"Invalid Start response: "
                    f"status={response.status_code}, "
                    f"body={response.text[:300]!r}"
                )
                return

            if (
                response.ok
                and response_data.get("status") == "ok"
            ):
                response.success()

            else:
                response.failure(
                    f"Room entry rejected: "
                    f"status={response.status_code}, "
                    f"response={response_data}"
                )
                return

    
        # 3. Enter the experiment after validation
  

        entry_url = (
            self.start_url
            + "?welcome_page_ok=1"
        )

        with self.client.get(
            entry_url,
            name="Enter experiment",
            catch_response=True,
            allow_redirects=True,
        ) as response:

            newlink = response.url

            if (
                response.ok
                and newlink != entry_url
            ):
                response.success()

            else:
                response.failure(
                    f"Failed to enter experiment: "
                    f"status={response.status_code}, "
                    f"final_url={response.url}, "
                    f"body={response.text[:300]!r}"
                )
                return

        # 4. Continue through the oTree browser-bot pages
  

        status = True

        while status:

            request_name = ": ".join(
                newlink
                .strip("/")
                .split("/")[-3:]
            )

            with self.client.post(
                newlink,
                data={},
                name=request_name,
                catch_response=True,
                allow_redirects=True,
            ) as response:

                oldlink = newlink
                newlink = response.url

                if not response.ok:
                    response.failure(
                        f"oTree error: "
                        f"status={response.status_code}, "
                        f"url={response.url}, "
                        f"body={response.text[:300]!r}"
                    )
                    status = False

                elif oldlink == newlink:
                    response.success()
                    status = False

                else:
                    response.success()


class OtreeTaskSet(TaskSet):

    def on_start(self):

        room_path = (
            "/room/test"
        )

        full_url = (
            self.user.host.rstrip("/")
            + room_path
        )

        self.otree_client = OtreeApplication(
            client=self.client,
            start_url=full_url,
        )

    @task
    def start_bot(self):

        self.otree_client.run_experiment()

        raise StopUser()


class WebsiteUser(HttpUser):

    host = "http://localhost:8000"

    tasks = [OtreeTaskSet]