// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * EPIC 3 - Immutable Vote Ledger (Permissioned)
 * Stores ONLY hashes + Merkle roots (no plaintext votes).
 * Simulates BFT-style commit via quorum approvals.
 */
contract VoteLedger {
    address public admin;
    uint256 public quorum; // e.g., 2 or 3 approvals required

    mapping(address => bool) public isNode;

    struct BlockHeader {
        uint256 height;
        bytes32 prevHash;
        bytes32 merkleRoot;
        uint256 entryCount;
        bytes32 blockHash;
        uint256 timestamp;
    }

    // electionIdHash => height => header
    mapping(bytes32 => mapping(uint256 => BlockHeader)) public blocks;

    // electionIdHash => tip height/hash
    mapping(bytes32 => uint256) public tipHeight;
    mapping(bytes32 => bytes32) public tipHash;

    // proposal approvals: electionIdHash => blockHash => approvalsCount
    mapping(bytes32 => mapping(bytes32 => uint256)) public approvalsCount;
    mapping(bytes32 => mapping(bytes32 => mapping(address => bool))) public approvedBy;

    // proposal header staging: electionIdHash => blockHash => header
    mapping(bytes32 => mapping(bytes32 => BlockHeader)) public proposals;
    mapping(bytes32 => mapping(bytes32 => bool)) public proposalExists;
    mapping(bytes32 => mapping(bytes32 => bool)) public finalized;

    event NodeUpdated(address node, bool allowed);
    event QuorumUpdated(uint256 quorum);

    event BlockProposed(bytes32 electionIdHash, bytes32 blockHash, uint256 height, bytes32 merkleRoot);
    event BlockApproved(bytes32 electionIdHash, bytes32 blockHash, address approver, uint256 approvals);
    event BlockFinalized(bytes32 electionIdHash, bytes32 blockHash, uint256 height);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    modifier onlyNode() {
        require(isNode[msg.sender], "Not authorized node");
        _;
    }

    constructor(uint256 _quorum) {
        admin = msg.sender;
        quorum = _quorum;
        isNode[msg.sender] = true; // deployer becomes first node
        emit NodeUpdated(msg.sender, true);
        emit QuorumUpdated(_quorum);
    }

    function setNode(address node, bool allowed) external onlyAdmin {
        isNode[node] = allowed;
        emit NodeUpdated(node, allowed);
    }

    function setQuorum(uint256 _quorum) external onlyAdmin {
        require(_quorum >= 1, "quorum too low");
        quorum = _quorum;
        emit QuorumUpdated(_quorum);
    }

    function getTip(bytes32 electionIdHash) external view returns (uint256, bytes32) {
        return (tipHeight[electionIdHash], tipHash[electionIdHash]);
    }

    function getBlock(bytes32 electionIdHash, uint256 height) external view returns (BlockHeader memory) {
        return blocks[electionIdHash][height];
    }

    function proposeBlock(
        bytes32 electionIdHash,
        uint256 height,
        bytes32 prevHash,
        bytes32 merkleRoot,
        uint256 entryCount
    ) external onlyNode returns (bytes32) {
        // enforce monotonic height
        require(height == tipHeight[electionIdHash] + 1, "Bad height");
        require(prevHash == tipHash[electionIdHash], "Bad prev hash");

        bytes32 blockHash = keccak256(
            abi.encodePacked(electionIdHash, height, prevHash, merkleRoot, entryCount)
        );

        require(!proposalExists[electionIdHash][blockHash], "Already proposed");

        BlockHeader memory hdr = BlockHeader({
            height: height,
            prevHash: prevHash,
            merkleRoot: merkleRoot,
            entryCount: entryCount,
            blockHash: blockHash,
            timestamp: block.timestamp
        });

        proposals[electionIdHash][blockHash] = hdr;
        proposalExists[electionIdHash][blockHash] = true;

        emit BlockProposed(electionIdHash, blockHash, height, merkleRoot);

        // proposer auto-approves
        _approve(electionIdHash, blockHash);

        return blockHash;
    }

    function approveBlock(bytes32 electionIdHash, bytes32 blockHash) external onlyNode {
        require(proposalExists[electionIdHash][blockHash], "No such proposal");
        require(!finalized[electionIdHash][blockHash], "Already finalized");
        _approve(electionIdHash, blockHash);
    }

    function _approve(bytes32 electionIdHash, bytes32 blockHash) internal {
        if (!approvedBy[electionIdHash][blockHash][msg.sender]) {
            approvedBy[electionIdHash][blockHash][msg.sender] = true;
            approvalsCount[electionIdHash][blockHash] += 1;

            emit BlockApproved(
                electionIdHash,
                blockHash,
                msg.sender,
                approvalsCount[electionIdHash][blockHash]
            );
        }
    }

    function finalizeBlock(bytes32 electionIdHash, bytes32 blockHash) external onlyNode {
        require(proposalExists[electionIdHash][blockHash], "No such proposal");
        require(!finalized[electionIdHash][blockHash], "Already finalized");
        require(approvalsCount[electionIdHash][blockHash] >= quorum, "Not enough approvals");

        BlockHeader memory hdr = proposals[electionIdHash][blockHash];

        blocks[electionIdHash][hdr.height] = hdr;
        tipHeight[electionIdHash] = hdr.height;
        tipHash[electionIdHash] = hdr.blockHash;

        finalized[electionIdHash][blockHash] = true;

        emit BlockFinalized(electionIdHash, blockHash, hdr.height);
    }
}
