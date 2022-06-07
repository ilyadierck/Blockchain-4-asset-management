// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

struct Asset{
    string ipfsUrl;
    string[] pastVersions;
}

contract AssetManager {
    StorageContract store = new StorageContract();

    function addAsset(string memory id, string memory ipfsUrl) public{
        store.saveNewAsset(id, ipfsUrl);
    }

    function editAsset(string memory oldId, string memory oldIpfsUrl, string memory newIpfsUrl) public{
        store.editAsset(oldId, oldIpfsUrl, newIpfsUrl);
    }

    function getAsset(string memory id) public view returns (Asset memory){
        return store.getAsset(id);
    }
}

contract StorageContract{
    mapping(string => Asset) public assets;

    function saveNewAsset(string memory id, string memory ipfsUrl) external{
        assets[id] = Asset(ipfsUrl, new string[](10));
    }

    function saveNewAsset(string memory id, string memory ipfsUrl, string[] memory pastVersions) external{
        assets[id] = Asset(ipfsUrl, pastVersions);
    }

    function editAsset(string memory oldId, string memory oldIpfsUrl, string memory newIpfsUrl) external{
        assets[oldId].pastVersions.push(oldIpfsUrl);
        assets[oldId].ipfsUrl = newIpfsUrl;
    }

    function getAsset(string memory id) external view returns(Asset memory){
        return assets[id];
    }
}