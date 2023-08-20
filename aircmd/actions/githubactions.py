from typing import Any, Dict

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
