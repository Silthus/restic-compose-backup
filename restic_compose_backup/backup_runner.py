import logging
import os
import docker

from restic_compose_backup.config import Config

logger = logging.getLogger(__name__)


def run(image: str = None, command: str = None, volumes: dict = None,
        environment: dict = None, labels: dict = None, source_container_id: str = None):
    logger.info("Starting backup container")
    config = Config()
    client = docker.DockerClient(base_url=config.docker_base_url)

    container = client.containers.run(
        image,
        command,
        labels=labels,
        # auto_remove=True,  # We remove the container further down
        detach=True,
        environment=environment,
        volumes=volumes,
        network_mode=f'container:{source_container_id}',  # Reuse original container's network stack.
        working_dir=os.getcwd(),
        tty=True,
    )

    logger.info("Backup process container: %s", container.name)
    log_generator = container.logs(stdout=True, stderr=True, stream=True, follow=True)

    def readlines(stream):
        """Read stream line by line"""
        while True:
            line = ""
            while True:
                try:
                    line += next(stream).decode()
                    if line.endswith('\n'):
                        break
                except StopIteration:
                    break
            if line:
                yield line.rstrip()
            else:
                break

    with open('backup.log', 'w') as fd:
        for line in readlines(log_generator):
            fd.write(line)
            fd.write('\n')
            logger.info(line)


    container.reload()
    logger.debug("Container ExitCode %s", container.attrs['State']['ExitCode'])
    container.remove()

    return container.attrs['State']['ExitCode']