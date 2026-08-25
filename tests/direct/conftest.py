import os
import sys
import tempfile

import pytest
from gltest.direct import loader
from gltest.direct.loader import deploy_contract


def _inject_message_to_fd0_windows(vm):
    from genlayer.py import calldata
    from genlayer.py.types import Address

    sender = Address(vm.sender) if isinstance(vm.sender, bytes) else vm.sender
    contract = Address(vm._contract_address) if isinstance(vm._contract_address, bytes) else vm._contract_address
    origin = Address(vm.origin) if isinstance(vm.origin, bytes) else vm.origin
    encoded = calldata.encode({
        "contract_address": contract,
        "sender_address": sender,
        "origin_address": origin,
        "stack": [],
        "value": vm._value,
        "datetime": vm._datetime,
        "is_init": False,
        "chain_id": vm._chain_id,
        "entry_kind": 0,
        "entry_data": b"",
        "entry_stage_data": None,
    })
    fd, path = tempfile.mkstemp()
    os.write(fd, encoded)
    os.lseek(fd, 0, os.SEEK_SET)
    vm._original_stdin_fd = os.dup(0)
    os.dup2(fd, 0)
    os.close(fd)
    vm._message_temp_path = path


def _clear_placeholder_genlayer():
    for module_name in tuple(sys.modules):
        if module_name == "genlayer" or module_name.startswith("genlayer."):
            del sys.modules[module_name]


def _restore_stdin_and_tempfile(vm):
    original_stdin_fd = getattr(vm, "_original_stdin_fd", None)
    if original_stdin_fd is not None:
        os.dup2(original_stdin_fd, 0)
        os.close(original_stdin_fd)
        vm._original_stdin_fd = None
    temp_path = getattr(vm, "_message_temp_path", None)
    if temp_path is not None:
        os.unlink(temp_path)
        vm._message_temp_path = None


@pytest.fixture
def direct_deploy(direct_vm):
    def deploy(contract_path, *args, **kwargs):
        _clear_placeholder_genlayer()
        original_injector = loader._inject_message_to_fd0
        loader._inject_message_to_fd0 = _inject_message_to_fd0_windows
        try:
            return deploy_contract(contract_path, direct_vm, *args, **kwargs)
        finally:
            loader._inject_message_to_fd0 = original_injector
            _restore_stdin_and_tempfile(direct_vm)

    return deploy
