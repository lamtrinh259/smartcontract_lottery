# with ETH = $1700 as of Aug 19th 2022, $50 = 0.0294ETH
# in wei, $50 = 29400000000000000
# Only run unit test in local development environment
from brownie import Lottery, accounts, network, config, exceptions
from web3 import Web3
from scripts.deploy_lottery import deploy_lottery
from scripts.helpful_scripts import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    get_account,
    fund_with_link,
    get_contract,
)
import pytest


def test_get_entrance_fee():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    # Arrange
    lottery = deploy_lottery()
    # Act
    # If ETH = 2000 USD, usdEntryFee = 50
    # 2000/1 = 50/x = 0.025
    expected_entrance_fee = Web3.toWei(0.025, "ether")
    entrance_fee = lottery.getEntranceFee()
    # Assert
    assert expected_entrance_fee == entrance_fee

    # old code
    # account = accounts[0]
    # lottery = Lottery.deploy(
    #     config["networks"][network.show_active()]["eth_usd_price_feed"],
    #     {"from": account},
    # )
    # assert lottery.getEntranceFee() > Web3.toWei(0.0290, "ether")
    # assert lottery.getEntranceFee() < Web3.toWei(0.045, "ether")


def test_cant_enter_unless_started():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    # Arrange
    lottery = deploy_lottery()
    # Act / Assert
    with pytest.raises(exceptions.VirtualMachineError):
        lottery.enter({"from": get_account(), "value": lottery.getEntranceFee()})


def test_can_start_and_enter_lottery():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    # Arrange
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    # Act
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    # Assert
    assert lottery.players(0) == account


def test_can_end_lottery():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    # Arrange
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    # Act
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    fund_with_link(lottery)
    lottery.endLottery({"from": account})
    # Assert
    assert lottery.lottery_state() == 2


def test_can_pick_winner_correctly():
    """Most complicated and important test"""
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    # Arrange
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    lottery.enter({"from": get_account(index=1), "value": lottery.getEntranceFee()})
    lottery.enter({"from": get_account(index=2), "value": lottery.getEntranceFee()})
    fund_with_link(lottery)
    transaction = lottery.endLottery({"from": account})
    # '.events' is attribute
    request_id = transaction.events["RequestedRandomness"]["requestId"]
    STATIC_RNG = 777
    get_contract("vrf_coordinator").callBackWithRandomness(
        request_id, STATIC_RNG, lottery.address, {"from": account}
    )
    starting_balance_of_account = account.balance()
    balance_of_lottery = lottery.balance()
    # 777 mod 3 == 0
    # Assert
    assert lottery.recentWinner() == account
    assert lottery.balance() == 0
    assert account.balance() == starting_balance_of_account + balance_of_lottery
