pragma solidity ^0.8.0;

contract EduTrack {
    struct ProgressRecord {
        string studentId;
        string dataHash;
        uint256 timestamp;
        string metadata;
        address recordedBy;
    }
    
    mapping(string => ProgressRecord[]) private studentRecords;
    mapping(string => mapping(string => bool)) private studentHashes;
    
    address public owner;
    uint256 public recordCount;
    
    event ProgressRecorded(
        string indexed studentId,
        string dataHash,
        uint256 timestamp,
        address recordedBy
    );
    
    event ProgressVerified(
        string indexed studentId,
        string dataHash,
        bool isValid
    );
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can perform this action");
        _;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    function recordProgress(
        string memory studentId,
        string memory dataHash,
        uint256 timestamp,
        string memory metadata
    ) public onlyOwner returns (bool) {
        require(bytes(studentId).length > 0, "Student ID cannot be empty");
        require(bytes(dataHash).length > 0, "Data hash cannot be empty");
        require(timestamp > 0, "Invalid timestamp");
        
        // Check if this hash already exists for the student
        require(!studentHashes[studentId][dataHash], "Duplicate record detected");
        
        ProgressRecord memory newRecord = ProgressRecord({
            studentId: studentId,
            dataHash: dataHash,
            timestamp: timestamp,
            metadata: metadata,
            recordedBy: msg.sender
        });
        
        studentRecords[studentId].push(newRecord);
        studentHashes[studentId][dataHash] = true;
        recordCount++;
        
        emit ProgressRecorded(studentId, dataHash, timestamp, msg.sender);
        return true;
    }
    
    function verifyProgress(
        string memory studentId,
        string memory dataHash
    ) public view returns (bool) {
        return studentHashes[studentId][dataHash];
    }
    
    function getStudentRecordCount(string memory studentId) public view returns (uint256) {
        return studentRecords[studentId].length;
    }
    
    function getStudentRecord(
        string memory studentId,
        uint256 index
    ) public view returns (
        string memory dataHash,
        uint256 timestamp,
        string memory metadata,
        address recordedBy
    ) {
        require(index < studentRecords[studentId].length, "Index out of bounds");
        
        ProgressRecord memory record = studentRecords[studentId][index];
        return (
            record.dataHash,
            record.timestamp,
            record.metadata,
            record.recordedBy
        );
    }
    
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "Invalid new owner address");
        owner = newOwner;
    }
}