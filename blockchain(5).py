"""
In this assignment you will extend and implement a class framework to create a simple but functional blockchain that combines the ideas of proof-of-work, transactions, blocks, and blockchains.
You may create new member functions, but DO NOT MODIFY any existing APIs.  These are the interface into your blockchain.


This blockchain has the following consensus rules (it is a little different from Bitcoin to make testing easier):

Blockchain

1. There are no consensus rules pertaining to the minimum proof-of-work of any blocks.  That is it has no "difficulty adjustment algorithm".
Instead, your code will be expected to properly place blocks of different difficulty into the correct place in the blockchain and discover the most-work tip.

2. A block with no transactions (no coinbase) is valid (this will help us isolate tests).

3. If a block as > 0 transactions, the first transaction MUST be the coinbase transaction.

Block Merkle Tree

1. You must use sha256 hash 
2. You must use 0 if additional items are needed to pad odd merkle levels
(more specific information is included below)

Transactions

1. A transaction with inputs==None is a valid mint (coinbase) transaction.  The coins created must not exceed the per-block "minting" maximum.

2. If the transaction is not a coinbase transaction, coins cannot be created.  In other words, coins spent (inputs) must be >= coins sent (outputs).

3. Constraint scripts (permission to spend) are implemented via python lambda expressions (anonymous functions).  These constraint scripts must accept a list of parameters, and return True if
   permission to spend is granted.  If execution of the constraint script throws an exception or returns anything except True do not allow spending!

461: You may assume that every submitted transaction is correct.
     This means that you should just make the Transaction validate() function return True
     You do not need to worry about tracking the UTXO (unspent transaction outputs) set.

661: You need to verify transactions, their constraint and satisfier scripts, and track the UTXO set.


Some useful library functions:

Read about hashlib.sha256() to do sha256 hashing in python.
Convert the sha256 array of bytes to a big endian integer via: int.from_bytes(bunchOfBytes,"big")

Read about the "dill" library to serialize objects automatically (dill.dumps()).  "Dill" is like "pickle", but it can serialize python lambda functions, which you need to install via "pip3 install dill".  The autograder has this library pre-installed.
You'll probably need this when calculating a transaction id.

"""
import sys
assert sys.version_info >= (3, 6)
import hashlib
import dill as serializer

class Output:
    """ This models a transaction output """
    def __init__(self, constraint = None, amount = 0):
        """ constraint is a function that takes 1 argument which is a list of 
            objects and returns True if the output can be spent.  For example:
            Allow spending without any constraints (the "satisfier" in the Input object can be anything)
            lambda x: True

            Allow spending if the spender can add to 100 (example: satisfier = [40,60]):
            lambda x: x[0] + x[1] == 100

            If the constraint function throws an exception, do not allow spending.
            For example, if the satisfier = ["a","b"] was passed to the previous constraint script

            If the constraint is None, then allow spending without constraint

            amount is the quantity of tokens associated with this output """
        self.constraint = constraint if constraint is not None else (lambda x: True)
        self.amount = amount

    def can_spend(self, satisfier):
        try:
            return self.constraint(satisfier)
        except Exception:
            return False

class Input:
    """ This models an input (what is being spent) to a blockchain transaction """
    def __init__(self, txHash, txIdx, satisfier):
        """ This input references a prior output by txHash and txIdx.
            txHash is therefore the prior transaction hash
            txIdx identifies which output in that prior transaction is being spent.  It is a 0-based index.
            satisfier is a list of objects that is be passed to the Output constraint script to prove that the output is spendable.
        """
        self.txHash = txHash      
        self.txIdx = txIdx        
        self.satisfier = satisfier

    def get_reference(self):
        return (self.txHash, self.txIdx)

    def get_satisfier(self):
        return self.satisfier
    

class Transaction:
    """ This is a blockchain transaction """
    def __init__(self, inputs=None, outputs=None, data = None):
        """ Initialize a transaction from the provided parameters.
            inputs is a list of Input objects that refer to unspent outputs.
            outputs is a list of Output objects.
            data is a byte array to let the transaction creator put some 
              arbitrary info in their transaction.
        """
        self.inputs = inputs if inputs is not None else []
        self.outputs = outputs if outputs is not None else []
        self.data = data if data is not None else b''

    def getHash(self):
        """Return this transaction's probabilistically unique identifier as a big-endian integer"""
        tx_data = serializer.dumps((self.inputs, self.outputs, self.data))
        return int.from_bytes(hashlib.sha256(tx_data).digest(), "big")

    def getInputs(self):
        """ return a list of all inputs that are being spent """
        return self.inputs

    def getOutput(self, n):
        """ Return the output at a particular index """
        if 0 <= n < len(self.outputs):
            return self.outputs[n]
        return None  

    def validateMint(self, maxCoinsToCreate):
        """ Validate a mint (coin creation) transaction.
            A coin creation transaction should have no inputs,
            and the sum of the coins it creates must be less than maxCoinsToCreate.
        """
        if self.inputs:
            return False
        
        output = sum(output.amount for output in self.outputs)
        return output <= maxCoinsToCreate

    def validate(self, unspentOutputDict):
        """ Validate this transaction given a dictionary of unspent transaction outputs.
            unspentOutputDict is a dictionary of items of the following format: { (txHash, offset) : Output }
        """
        tinput = 0
        toutput = sum(o.amount for o in self.outputs)

        for i_obj in self.inputs:
            ref = i_obj.get_reference()

            if ref not in unspentOutputDict:
                return False

            o_spent = unspentOutputDict[ref]
            if not o_spent.can_spend(i_obj.get_satisfier()):
                return False

            tinput += o_spent.amount

        return tinput >= toutput


class HashableMerkleTree:
    """ A merkle tree of hashable objects.

        If no transaction or leaf exists, use 32 bytes of 0.
        The list of objects that are passed must have a member function named
        .getHash() that returns the object's sha256 hash as an big endian integer.

        Your merkle tree must use sha256 as your hash algorithm and big endian
        conversion to integers so that the tree root is the same for everybody.
        This will make it easy to test.

        If a level has an odd number of elements, append a 0 value element.
        if the merkle tree has no elements, return 0.

    """

    def __init__(self, hashableList = None):
        self.leaves = hashableList if hashableList else []

    def calcMerkleRoot(self):
        """ Calculate the merkle root of this tree."""
        if not self.leaves:
            return 0  

        cur_level = [ob.getHash() for ob in self.leaves]

        while len(cur_level) > 1:
            n_level = []

            for i in range(0, len(cur_level), 2):
                left = cur_level[i]
                right = cur_level[i + 1] if i + 1 < len(cur_level) else 0

                combined = hashlib.sha256((left.to_bytes(32, "big") +
                                                right.to_bytes(32, "big"))).digest()
                n_level.append(int.from_bytes(combined, "big"))

            cur_level = n_level

        return cur_level[0]


class BlockContents:
    """ The contents of the block (merkle tree of transactions)
        This class isn't really needed.  I added it so the project could be cut into
        just the blockchain logic, and the blockchain + transaction logic.
    """
    def __init__(self):
        self.data = HashableMerkleTree() 

    def setData(self, d):
        self.data = HashableMerkleTree(d)

    def getData(self):
        return self.data

    def calcMerkleRoot(self):
        return self.data.calcMerkleRoot()

class Block:
    """ This class should represent a blockchain block.
        It should have the normal fields needed in a block and also an instance of "BlockContents"
        where we will store a merkle tree of transactions.
    """
    def __init__(self):
        self.contents = BlockContents()
        self.priorBlockHash = None       
        self.target = None                
        self.nonce = 0                    
        self.utxo_set = {}                

    def getContents(self):
        """ Return the Block content (a BlockContents object)"""
        return self.contents

    def setContents(self, data):
        """ set the contents of this block's merkle tree to the list of objects in the data parameter """
        self.contents.setData(data)

    def setTarget(self, target):
        """ Set the difficulty target of this block """
        self.target = target

    def getTarget(self):
        """ Return the difficulty target of this block """
        return self.target

    def getHash(self):
        """ Calculate the hash of this block. Return as an integer """
        header = (str(self.priorBlockHash) + str(self.contents.calcMerkleRoot()) + 
                  str(self.target) + str(self.nonce)).encode()
        return int.from_bytes(hashlib.sha256(header).digest(), "big")

    def setPriorBlockHash(self, priorHash):
        """ Assign the parent block hash """
        self.priorBlockHash = priorHash

    def getPriorBlockHash(self):
        """ Return the parent block hash """
        return self.priorBlockHash

    def mine(self, tgt):
        """Update the block header to the passed target (tgt) and then search for a nonce which produces a block whose hash is less than the target, "solving" the block"""
        self.target = tgt
        while self.getHash() >= tgt:
            self.nonce += 1

    def validate(self, unspentOutputs, maxMint):
        """ Given a dictionary of unspent outputs, and the maximum amount of
            coins that this block can create, determine whether this block is valid.
            Valid blocks satisfy the POW puzzle, have a valid coinbase tx, and have valid transactions (if any exist).

            Return None if the block is invalid.

            Return something else if the block is valid

            661 hint: you may want to return a new unspent output object (UTXO set) with the transactions in this
            block applied, for your own use when implementing other APIs.

            461: you can ignore the unspentOutputs field (just pass {} when calling this function)
        """
        if self.getHash() >= self.target:
            return None

        n_utxo = unspentOutputs.copy()
        transactions = self.contents.getData().leaves  
        c_found = False

        for idx, tx in enumerate(transactions):
            if idx == 0:
                if not tx.validateMint(maxMint):
                    return None
                c_found = True
            else:
                if not tx.validate(n_utxo):
                    return None

            for i, output in enumerate(tx.outputs):
                n_utxo[(tx.getHash(), i)] = output

            for i_obj in tx.getInputs():
                ref = i_obj.get_reference()
                if ref in n_utxo:
                    del n_utxo[ref]

        if len(transactions) > 0 and not c_found:
            return None

        return n_utxo

class Blockchain(object):

    def __init__(self, genesisTarget, maxMintCoinsPerTx):
        """ Initialize a new blockchain and create a genesis block.
            genesisTarget is the difficulty target of the genesis block (that you should create as part of this initialization).
            maxMintCoinsPerTx is a consensus parameter -- don't let any block into the chain that creates more coins than this!
        """
        self.blocks = {}  
        self.height_blocks = {}  
        self.maxMintCoinsPerTx = maxMintCoinsPerTx
        self.genesisTarget = genesisTarget

        self.genesis_utxo_set = {}
        
        genesis_block = Block()
        genesis_block.setTarget(genesisTarget)
        genesis_block.mine(genesisTarget)
        genesis_block.utxo_set = self.genesis_utxo_set  
        self.add_block(genesis_block)

    def getTip(self):
        """ Return the block at the tip (end) of the blockchain fork that has the largest amount of work"""
        m_work = -1
        tip_block = None

        for blk in self.blocks.values():
            blk_work = self.getCumulativeWork(blk.getHash())
            if blk_work and blk_work > m_work:
                m_work = blk_work
                tip_block = blk
        return tip_block

    def getWork(self, target):
        """Get the "work" needed for this target.  Work is the ratio of the genesis target to the passed target"""
        return self.genesisTarget / target  

    def getCumulativeWork(self, blkHash):
        """Return the cumulative work for the block identified by the passed hash.  Return None if the block is not in the blockchain"""
        blk = self.blocks.get(blkHash)
        if not blk:
            return None

        cumul_work = 0
        while blk:
            cumul_work += self.getWork(blk.getTarget())
            blk = self.blocks.get(blk.getPriorBlockHash())
        
        return cumul_work

    def getBlocksAtHeight(self, height):
        """Return an array of all blocks in the blockchain at the passed height (including all forks)"""
        return self.height_blocks.get(height, [])

    def extend(self, block):
        """Adds this block into the blockchain in the proper location, if it is valid.  The "proper location" may not be the tip!

           Hint: Note that this means that you must validate transactions for a block that forks off of any position in the blockchain.
           The easiest way to do this is to remember the UTXO set state for every block, not just the tip.
           For space efficiency "real" blockchains only retain a single UTXO state (the tip).  This means that during a blockchain reorganization
           they must travel backwards up the fork to the common block, "undoing" all transaction state changes to the UTXO, and then back down
           the new fork.  For this assignment, don't implement this detail, just retain the UTXO state for every block
           so you can easily "hop" between tips.

           Return false if the block is invalid (breaks any miner constraints), and do not add it to the blockchain."""
        if block.getPriorBlockHash() is not None and block.getPriorBlockHash() not in self.blocks:
            return False

        p_block = self.blocks[block.getPriorBlockHash()]
        p_set = p_block.utxo_set.copy() if p_block else self.genesis_utxo_set

        n_set = block.validate(p_set, self.maxMintCoinsPerTx)
        if n_set is None:
            return False  
        
        blk_hash = block.getHash()
        self.blocks[blk_hash] = block

        block.utxo_set = n_set
        block.height = p_block.height + 1 if p_block else 0

        if block.height not in self.height_blocks:
            self.height_blocks[block.height] = []
        self.height_blocks[block.height].append(block)

        return True
    
    def add_block(self, block):
        """
        A helper function to add a block to both blocks and height-based storage.
        
        Args:
            block: The block to add.
        """
        block_hash = block.getHash()
        self.blocks[block_hash] = block
        block.height = 0  
        self.height_blocks[0] = [block] 


# --------------------------------------------
# You should make a bunch of your own tests before wasting time submitting stuff to gradescope.
# Its a LOT faster to test locally.  Try to write a test for every API and think about weird cases.

# Let me get you started:
def Test():
    # test creating blocks, mining them, and verify that mining with a lower target results in a lower hash
    b1 = Block()
    b1.mine(int("F"*64,16))
    h1 = b1.getHash()
    b2 = Block()
    b2.mine(int("F"*63,16))
    h2 = b2.getHash()
    assert h2 < h1

    t0 = Transaction(None, [Output(lambda x: True, 100)])
    # Negative test: minted too many coins
    assert t0.validateMint(50) == False, "1 output: tx minted too many coins"
    # Positive test: minted the right number of coins
    assert t0.validateMint(100) == True, "1 output: tx minted the right number of coins"

    class GivesHash:
        def __init__(self, hash):
            self.hash = hash
        def getHash(self):
            return self.hash

    assert HashableMerkleTree([GivesHash(x) for x in [106874969902263813231722716312951672277654786095989753245644957127312510061509]]).calcMerkleRoot().to_bytes(32,"big").hex() == "ec4916dd28fc4c10d78e287ca5d9cc51ee1ae73cbfde08c6b37324cbfaac8bc5"

    assert HashableMerkleTree([GivesHash(x) for x in [106874969902263813231722716312951672277654786095989753245644957127312510061509, 66221123338548294768926909213040317907064779196821799240800307624498097778386, 98188062817386391176748233602659695679763360599522475501622752979264247167302]]).calcMerkleRoot().to_bytes(32,"big").hex() == "ea670d796aa1f950025c4d9e7caf6b92a5c56ebeb37b95b072ca92bc99011c20"

    print ("yay local tests passed")