import os
import platform
from typing import Callable, List, Optional

import platformdirs
import pygit2
from dagger import Container
from pydantic import BaseSettings, Field, SecretStr

from .singleton import Singleton


def get_git_revision() -> str:
    repo = pygit2.Repository(".") 
    commit_hash = repo.revparse_single("HEAD").short_id
    return commit_hash

def get_current_branch() -> str:    
    repo = pygit2.Repository(".")                                                                                                                                                                                                                                                                                                                           
    return repo.head.shorthand                                                                                                                                                                   
                                                                                                                                                                                                
def get_latest_commit_message() -> str:   
    repo = pygit2.Repository(".")                                                                                                                                                                                                                                                                                                                      
    commit = repo[repo.head.target]                                                                                                                                                              
    return commit.message                                                                                                                                                                        
                                                                                                                                                                                                
def get_latest_commit_author() -> str:  
    repo = pygit2.Repository(".")                                                                                                                                                                                                                                                                                                                       
    commit = repo[repo.head.target]                                                                                                                                                              
    return commit.author.name                                                                                                                                                                    
                                                                                                                                                                                                
def get_latest_commit_time() -> str:    
    repo = pygit2.Repository(".")                                                                                                                                                                                                                                                                                                                      
    commit = repo[repo.head.target]                                                                                                                                                              
    return str(commit.commit_time)       

def get_repo_root_path() -> str:
    repo = pygit2.Repository(".")
    return os.path.dirname(os.path.dirname(repo.path))

# Immutable. Use this for application configuration. Created at bootstrap.
class GlobalSettings(BaseSettings, Singleton):
    GITHUB_TOKEN: Optional[str] = Field(None, env="GITHUB_TOKEN")
    GIT_CURRENT_REVISION: str = Field(default_factory=get_git_revision)                                                                                                                                  
    GIT_CURRENT_BRANCH: str = Field(default_factory=get_current_branch)                                                                                                                              
    GIT_LATEST_COMMIT_MESSAGE: str = Field(default_factory=get_latest_commit_message)                                                                                                                
    GIT_LATEST_COMMIT_AUTHOR: str = Field(default_factory=get_latest_commit_author)                                                                                                                  
    GIT_LATEST_COMMIT_TIME: str = Field(default_factory=get_latest_commit_time)       
    GIT_REPO_ROOT_PATH: str = Field(default_factory=get_repo_root_path)
    CI: bool = Field(False, env="CI")
    LOG_LEVEL: str = Field("WARNING", env="LOG_LEVEL")
    PLATFORM: str = platform.system()
    POETRY_CACHE_DIR: str = Field(
        default_factory=lambda: platformdirs.user_cache_dir("pypoetry"),
        env="POETRY_CACHE_DIR"
    )
    MYPY_CACHE_DIR: str = Field("~/.cache/.mypy_cache", env="MYPY_CACHE_DIR")
    DEFAULT_PYTHON_EXCLUDE: List[str] = Field(["**/.venv", "**/__pycache__"], env="DEFAULT_PYTHON_EXCLUDE")
    DEFAULT_EXCLUDED_FILES: List[str] = Field(
        [
            ".git",
            "**/build",
            "**/.venv",
            "**/secrets",
            "**/__pycache__",
            "**/*.egg-info",
            "**/.vscode",
            "**/.pytest_cache",
            "**/.eggs",
            "**/.mypy_cache",
            "**/.DS_Store",
        ],
        env="DEFAULT_EXCLUDED_FILES"
    )
    DOCKER_VERSION:str = Field("20.10.23", env="DOCKER_VERSION")
    DOCKER_DIND_IMAGE: str = Field("docker:20-dind", env="DOCKER_DIND_IMAGE")
    DOCKER_CLI_IMAGE: str = Field("docker:20-cli", env="DOCKER_CLI_IMAGE")
    GRADLE_CACHE_PATH: str = Field("/root/.gradle", env="GRADLE_CACHE_PATH")
    GRADLE_BUILD_CACHE_PATH: str = Field(f"{GRADLE_CACHE_PATH}/build-cache-1", env="GRADLE_BUILD_CACHE_PATH")
    GRADLE_READ_ONLY_DEPENDENCY_CACHE_PATH: str = Field("/root/gradle_dependency_cache", env="GRADLE_READ_ONLY_DEPENDENCY_CACHE_PATH")

    PREFECT_API_URL: str = Field("http://127.0.0.1:4200/api", env="PREFECT_API_URL")
    PREFECT_COMMA_DELIMITED_USER_TAGS: str = Field("", env="PREFECT_COMMA_DELIMITED_USER_TAGS")
    PREFECT_COMMA_DELIMITED_SYSTEM_TAGS: str = Field("CI:False", env="PREFECT_COMMA_DELIMITED_SYSTEM_TAGS")

    SECRET_DOCKER_HUB_USERNAME: Optional[SecretStr] = Field(None, env="SECRET_DOCKER_HUB_USERNAME")
    SECRET_DOCKER_HUB_PASSWORD: Optional[SecretStr] = Field(None, env="SECRET_DOCKER_HUB_PASSWORD")
    
    PIP_CACHE_DIR: str = Field(
        default_factory=lambda: platformdirs.user_cache_dir("pip"),
        env="PIP_CACHE_DIR"
    )

    class Config:                                                                                                                                                        
         arbitrary_types_allowed = True                                                                                                                                   
         env_file = '.env' 


'''
If both include and exclude are supplied, the load_settings function will first filter the environment variables based on the include list, and then it will    
further filter the resulting environment variables based on the exclude list.                                                                                   

Here's the order of operations:                                                                                                                                 

 1 If include is provided, only the environment variables with keys in the include list will be considered.                                                     
 2 If exclude is provided, any environment variables with keys in the exclude list will be removed from the filtered list obtained in step 1.                   
 3 The remaining environment variables will be loaded into the container.   
'''                                                                                                             
                                                                                                                                                                
def load_settings(settings: GlobalSettings, include: Optional[List[str]] = None, exclude: Optional[List[str]] = None) -> Callable[[Container], Container]:     
    def load_envs(ctr: Container) -> Container:                                                                                                                
        settings_dict = {key: value for key, value in settings.dict().items() if value is not None}                                                            
                                                                                                                                                            
        if include is not None:                                                                                                                                
            settings_dict = {key: settings_dict[key] for key in include if key in settings_dict}                                                               
                                                                                                                                                            
        if exclude is not None:                                                                                                                                
            settings_dict = {key: value for key, value in settings_dict.items() if key not in exclude}                                                         
                                                                                                                                                            
        for key, value in settings_dict.items():
            env_key = key.upper()
            ctr = ctr.with_env_variable(env_key, str(value))
                                                                                                                                                            
        return ctr                                                                                                                                             
                                                                                                                                                        
    return load_envs     
