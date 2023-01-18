@pytest.mark.asyncio
async def test_execute(account_factory):
    starknet, account = account_factory
    initializable = await starknet.deploy("contracts/Initializable.cairo")

    execution_info = await initializable.initialized().call()
    assert execution_info.result == (0,)

    await signer.send_transaction(account, initializable.contract_address, 'initialize', [])

    execution_info = await initializable.initialized().call()
    assert execution_info.result == (1,)
    
    #
# Storage
#

# Who owns/controls the car (can update signing authority)
@storage_var
func vehicle_owner_address(vehicle_id : felt) -> (address : felt):
end

# Who signs commitments on behalf of the car
@storage_var
func vehicle_signer_address(vehicle_id : felt) -> (address : felt):
end

# Hashes for vehicle state at some id
@storage_var
func vehicle_state(vehicle_id : felt, state_id : felt) -> (state_hash : felt):
end

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero
from starkware.starknet.common.syscalls import get_caller_address

...

# Initializes the vehicle with a given owner & signer
@external
func register_vehicle{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        vehicle_id : felt, signer_address : felt):
    # Verify that the vehicle ID is available
    let (is_vehicle_id_taken) = vehicle_owner_address.read(vehicle_id=vehicle_id)
    assert is_vehicle_id_taken = 0

    # Caller is the owner. Verify caller & signer are non zero
    let (owner_address) = get_caller_address()
    assert_not_zero(owner_address)
    assert_not_zero(signer_address)

    # Initialize the vehicle's owner and signer
    vehicle_owner_address.write(vehicle_id=vehicle_id, value=owner_address)
    vehicle_signer_address.write(vehicle_id=vehicle_id, value=signer_address)
    return ()
end

# Vehicle signers can attest to a state hash -- data storage & verification off-chain
@external
func attest_state{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        vehicle_id : felt, state_id : felt, state_hash : felt):
    # TODO: Verify the vehicle has been registered & the caller is the SIGNER (not the owner)
    # TODO: Make sure a unique state id was used

    # Register state
    vehicle_state.write(vehicle_id=vehicle_id, state_id=state_id, value=state_hash)
    return ()
end

from dataclasses import dataclass
from typing import Tuple

import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet, StarknetContract
from starkware.starkware_utils.error_handling import StarkException
from utils import Signer


some_vehicle = 1


@dataclass
class Account:
    signer: Signer
    contract: StarknetContract


@pytest.fixture(scope="module")
def event_loop():
    return asyncio.new_event_loop()


# Reusable local network & contracts to save testing time
@pytest.fixture(scope="module")
async def contract_factory() -> Tuple[Starknet, Account, Account, StarknetContract]:
    starknet = await Starknet.empty()
    some_signer = Signer(private_key=12345)
    owner_account = Account(
        signer=some_signer,
        contract=await starknet.deploy(
            "contracts/Account.cairo",
            constructor_calldata=[some_signer.public_key]
        )
    )
    some_other_signer = Signer(private_key=123456789)
    signer_account = Account(
        signer=some_other_signer,
        contract=await starknet.deploy(
            "contracts/Account.cairo",
            constructor_calldata=[some_other_signer.public_key]
        )
    )
    contract = await starknet.deploy("contracts/contract.cairo")
    return starknet, owner_account, signer_account, contract
