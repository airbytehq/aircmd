from typing import Any, Dict

from github import Github
from prefect import Flow, State
from prefect import settings as prefect_settings
from prefect.client.schemas.objects import FlowRun

from aircmd.models.settings import GlobalSettings


class MockPayloadBuilder:
    
    def __init__(self, settings: GlobalSettings):
        self.settings = settings
    
    def build_push_payload(self) -> Dict[str, Any]:
        return {
            "ref": self.settings.GIT_CURRENT_BRANCH,
            "repository": {
                "full_name": self.settings.GIT_REPOSITORY,
                "name": self.settings.GIT_REPOSITORY.split('/')[-1],  # Assuming the format is owner/repo
                "owner": {
                    "login": self.settings.GITHUB_ACTOR
                },
                "html_url": f"{self.settings.GITHUB_SERVER_URL}/{self.settings.GIT_REPOSITORY}"
            },
            "sender": {
                "type": "User",
                "login": self.settings.GITHUB_ACTOR
            },
            "pusher": {
                "name": self.settings.GITHUB_ACTOR
            },
            "head_commit": {
                "id": self.settings.GIT_CURRENT_REVISION,
                "message": self.settings.GIT_LATEST_COMMIT_MESSAGE,
                "author": {
                    "name": self.settings.GIT_LATEST_COMMIT_AUTHOR,
                    "email": "mockemail@example.com"
                },
                "timestamp": self.settings.GIT_LATEST_COMMIT_TIME
            }
        }

    def build_pull_request_payload(self, action: str = "opened") -> Dict[str, Any]:
        return {
            "action": action,
            "number": 1,
            "pull_request": {
                "number": 1,
                "body": "Mock PR Body",
                "html_url": f"{self.settings.GITHUB_SERVER_URL}/{self.settings.GIT_REPOSITORY}/pull/0",
                "head": {
                    "ref": self.settings.GIT_CURRENT_BRANCH,
                    "sha": self.settings.GIT_CURRENT_REVISION,
                    "repo": {
                        "full_name": self.settings.GIT_REPOSITORY
                    }
                }
            },
            "repository": {
                "full_name": self.settings.GIT_REPOSITORY,
                "name": self.settings.GIT_REPOSITORY.split('/')[-1],
                "owner": {
                    "login": self.settings.GITHUB_ACTOR
                },
                "html_url": f"{self.settings.GITHUB_SERVER_URL}/{self.settings.GIT_REPOSITORY}"
            },
            "sender": {
                "type": "User",
                "login": self.settings.GITHUB_ACTOR
            }
        }
    def build_workflow_dispatch_payload(self) -> Dict[str, Any]:
        return {
            "ref": self.settings.GIT_CURRENT_BRANCH,
            "repository": {
                "full_name": self.settings.GIT_REPOSITORY,
                "name": self.settings.GIT_REPOSITORY.split('/')[-1],  # Assuming the format is owner/repo
                "owner": {
                    "login": self.settings.GITHUB_ACTOR
                },
                "html_url": f"{self.settings.GITHUB_SERVER_URL}/{self.settings.GIT_REPOSITORY}"
            },
            "sender": {
                "type": "User",
                "login": self.settings.GITHUB_ACTOR
            },
            "workflow": {
                "id": 0,  # This would typically be a unique workflow ID.
                "name": "Mock Local CI Workflow",
                "state": "active"
            },
            "inputs": {
                # These are the inputs provided when triggering the workflow.
                # They might differ based on your workflow definition.
                # TODO: Add a way to specify these inputs when constructing the mock payload.
            }
        }

def create_status(settings: GlobalSettings, sha: str, state: str, context: str, description: str, target_url: str) -> None:
    g = Github(str(settings.GITHUB_TOKEN.get_secret_value() if settings.GITHUB_TOKEN else None))
    repo = g.get_repo(settings.GIT_REPOSITORY)
    
    repo.get_commit(sha).create_status(
        state=state,  # "error", "failure", "pending", or "success"
        target_url=target_url,
        description=description,
        context=context
    )

def github_status_update_hook(flow: Flow[Any, Any], flow_run: FlowRun, state: State[Any] | None) -> None:
    settings = GlobalSettings()
    sha = settings.GIT_CURRENT_REVISION
    assert flow_run.state is not None
    assert state is not None
    target_url = f"{prefect_settings.PREFECT_UI_URL.value()}/flow-runs/flow-run/{flow_run.state.state_details.flow_run_id}"
    context = flow.name

    if state.is_cancelled():
        status = "error"
        description = "This check was cancelled."
    elif state.is_failed():
        status = "failure"
        description = "This check failed."
    elif state.is_completed():
        status = "success"
        description = "This check succeeded."
    else:
        status = "pending"
        description = "This check is pending."
    
    create_status(settings, sha, status, context, description, target_url)
