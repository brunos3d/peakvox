"""Drivers package — concrete RuntimeDriver implementations.

This package is the only place in the backend that may import
substrate-specific libraries (e.g. docker, kubernetes). The
RuntimeManager depends only on the ``RuntimeDriver`` Protocol
defined in ``app.services.runtime_driver``; concrete drivers live
here.

Per ADR-0017 §5, the first concrete driver is
``DockerRuntimeDriver`` (Community Edition initial). Future drivers
(KubernetesRuntimeDriver for Cloud, PodmanRuntimeDriver for
rootless environments, LocalProcessDriver for development) are
separate ADRs and separate modules in this package.
"""
