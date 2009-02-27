'''
Core protocol classes. 

See http://fitnesse.org/FitNesse.SliM.SlimProtocol for more details.
    
The latest source code is available at http://code.launchpad.net/waferslim.

Copyright 2009 by the author(s). All rights reserved 
'''

from waferslim import WaferSlimException
from waferslim.execution import ExecutionContext, InstructionException, \
        NoSuchClassException, NoSuchConstructorException, \
        NoSuchInstanceException, NoSuchMethodException, \
        Make, Import, Call, CallAndAssign

class UnpackingError(WaferSlimException):
    ''' An attempt was made to unpack messages that do not conform 
    to the protocol spec '''  
    pass

_BYTE_ENCODING = 'utf-8'
_VERSION = 'Slim -- V0.0\n'
_START_CHUNK = '['
_END_CHUNK = ']'
_SEPARATOR = ':'
_SEPARATOR_LENGTH = len(_SEPARATOR.encode(_BYTE_ENCODING))
_NUMERIC_LENGTH = 6
_NUMERIC_ENCODING = '%%0%sd' % _NUMERIC_LENGTH
_NUMERIC_BLOCK_LENGTH = len((_NUMERIC_ENCODING % 0).encode(_BYTE_ENCODING)) \
    + _SEPARATOR_LENGTH
_ITEM_ENCODING = _NUMERIC_ENCODING + '%s%s'
_DISCONNECT = 'bye'
    
def unpack(packed_string):
    ''' Unpack a chunked-up packed_string into a list '''
    if isinstance(packed_string, str) \
    or isinstance(packed_string, unicode):
        chunks = []
        _unpack_chunk(packed_string, chunks)
        return chunks
    raise TypeError('%r is not a string' % packed_string)
    
def _unpack_chunk(packed_chunk, chunks):
    ''' Unpack a packed chunk, recursively if required '''
    _check_chunk(packed_chunk)
    pos = 1
    chunk_len = int(packed_chunk[pos:pos + _NUMERIC_LENGTH])
    _check_separator(packed_chunk, pos + _NUMERIC_LENGTH)
    pos += _NUMERIC_BLOCK_LENGTH 
    
    for i in range(0, chunk_len):
        item_len = int(packed_chunk[pos:pos + _NUMERIC_LENGTH])
        _check_separator(packed_chunk, pos + _NUMERIC_LENGTH)
        pos += _NUMERIC_BLOCK_LENGTH 
    
        item = packed_chunk[pos:pos + item_len]
        _check_separator(packed_chunk, pos + item_len)
        pos += (item_len + _SEPARATOR_LENGTH)
        
        if _is_chunk(item):
            sub_chunk = []
            _unpack_chunk(item, sub_chunk)
            chunks.append(sub_chunk)
        else:
            chunks.append(item)
    
def _check_chunk(packed_chunk):
    ''' Verify format of an packed_chunk '''
    _is_chunk(packed_chunk, raise_on_failure=True)
    
def _is_chunk(possible_chunk, raise_on_failure=False):
    ''' Check for indicative start/end of an encoded chunk '''
    if possible_chunk.startswith(_START_CHUNK):
        if possible_chunk.endswith(_END_CHUNK):
            return True
        elif raise_on_failure: 
            msg = '%r has no trailing %r' % (possible_chunk, _END_CHUNK)
        else:
            return False
    elif raise_on_failure: 
        msg = '%r has no leading %r' % (possible_chunk, _START_CHUNK)
    else:
        return False
    raise UnpackingError(msg)
    
def _check_separator(packed_chunk, pos):
    ''' Verify existence of separator at position pos in a packed_chunk '''
    if _SEPARATOR != packed_chunk[pos]:
        msg = '%r has no %r separator at pos %s' % \
                (packed_chunk, _SEPARATOR, pos)
        raise UnpackingError(msg)
    
def pack(item_list):
    ''' Pack each item from a list into the chunked-up format '''
    packed = [_pack_item(item) for item in item_list]
    packed.insert(0, _NUMERIC_ENCODING % len(item_list))
    return '%s%s%s%s' % (_START_CHUNK, _SEPARATOR.join(packed),
                         _SEPARATOR, _END_CHUNK)

def _pack_item(item): 
    ''' Pack (recursively if required) a single item in the format:  
    [iiiiii:llllll:item...]'''
    if isinstance(item, list):
        return _pack_item(pack(item))
    
    str_item = item and str(item) or 'null'
    return _ITEM_ENCODING % (len(str_item), _SEPARATOR, str_item)

_INSTRUCTION_TYPES = {'make':Make,
                      'import':Import,
                      'call':Call,
                      'callAndAssign':CallAndAssign }
_ID_POSITION = 0
_TYPE_POSITION = 1

def instruction_for(params):
    ''' Factory method for Instruction types '''
    instruction_type = params.pop(_TYPE_POSITION)
    instruction_id = params.pop(_ID_POSITION)
    return _INSTRUCTION_TYPES[instruction_type](instruction_id, params)

_OK = 'OK'
_EXCEPTION = '__EXCEPTION__:'
_EXCEPTIONS = {InstructionException:'MALFORMED_INSTRUCTION',
               NoSuchClassException:'NO_CLASS',
               NoSuchConstructorException:'COULD_NOT_INVOKE_CONSTRUCTOR',
               NoSuchInstanceException: 'NO_INSTANCE',
               NoSuchMethodException:'NO_METHOD_IN_CLASS'
              }

_NONE_STRING = '/__VOID__/'

class Results(object):
    ''' Collecting parameter for results of Instruction execute() methods '''
    NO_RESULT = object()
    
    def __init__(self):
        ''' Set up the list to hold the collected results '''
        self._collected = []
    
    def completed(self, instruction, result=NO_RESULT):
        ''' An instruction has completed, perhaps with a result '''
        if result == Results.NO_RESULT:
            str_result = _OK
        elif result:
            str_result = str(result)
        else:
            str_result = _NONE_STRING
        self._collected.append([instruction.instruction_id(), str_result])
          
    def raised(self, instruction, exception):
        ''' An instruction has raised an exception. The nature of the
        exception will be translated into the relevant Slim protocol format.'''
        self._collected.append([instruction.instruction_id(), 
                                self._translate(exception)])
    
    def _translate(self, exception):
        ''' Translate an exception type into a formatted message '''
        return '%s message:<<%s %s>>' % (_EXCEPTION, 
                                         _EXCEPTIONS[type(exception)], 
                                         exception.args[0])
    
    def collection(self):
        ''' Get the collected list of results - modifications to the list 
        will not be reflected in this collection '''
        collected = []
        collected.extend(self._collected)
        return collected

class Instructions(object):
    ''' Container for executable sequence of Instruction-s '''
    
    def __init__(self, unpacked_list, factory_method=instruction_for):
        ''' Provide an unpacked list of strings that will be converted 
        into a sequence of Instruction-s to execute '''
        self._unpacked_list = unpacked_list
        self._instruction_for = factory_method
    
    def execute(self, execution_context, results):
        ''' Create and execute Instruction-s, collecting the results '''
        for item in self._unpacked_list:
            instruction = self._instruction_for(item)
            instruction.execute(execution_context, results)
                
class RequestResponder(object):
    ''' Mixin class for responding to Slim requests.
    Logic mostly reverse engineered from Java test classes especially 
    fitnesse.responders.run.slimResponder.SlimTestSystemTest '''

    def respond_to_request(self, instructions=Instructions,
                                 execution_context=ExecutionContext,
                                 results=Results):
        ''' Entry point for mixin: respond to a Slim protocol request.
        Basic format of every interaction is:
        - every request requires an initial ACK with the Slim Version
        - messages can then be received and responses sent, in a loop
        - receiving a 'bye' message will terminate the loop 
        '''
        ack_bytes = self._send_ack(self.request)
        
        received, sent = self._message_loop(instructions,
                                            execution_context(),
                                            results())
        
        return received, sent + ack_bytes
    
    def _send_ack(self, request):
        ''' Acknowledge the request by sending the Slim Version '''
        response = _VERSION.encode(_BYTE_ENCODING)
        self.debug('Send Ack')
        return request.send(response)
    
    def _message_loop(self, instructions, execution_context, results):
        ''' Receive messages from the request and send responses.
        Each message starts with a numeric header (number of digits defined
        in _NUMERIC_LENGTH) which contains the byte length
        of the message contents. The message contents can then be read, 
        their instructions executed, and the results returned.'''
        received, sent = 0, 0
        
        while True:
            message_length, bytes_received = self._get_message_length()
            received += bytes_received
            data = self.request.recv(message_length).decode(_BYTE_ENCODING)
            self.debug('Recv message: %r' % data)
            received += message_length
            
            if _DISCONNECT == data:
                break
            else:
                instruction_list = instructions(unpack(data))
                instruction_list.execute(execution_context, results)
                response = pack(results.collection())
                formatted_response = self._format_response(response)
                sent += self.request.send(formatted_response)
                self.debug('Send response: %r' % response)
        
        return received, sent
    
    def _get_message_length(self):
        ''' Get the length of the message from an initial numeric header '''
        header_format = (_NUMERIC_ENCODING % 0) + _SEPARATOR 
        byte_size = len(header_format.encode(_BYTE_ENCODING))
        data = self.request.recv(byte_size).decode(_BYTE_ENCODING)
        length = int(data[0:_NUMERIC_LENGTH])
        return length, byte_size
    
    def _format_response(self, msg):
        ''' Encode the bytes and add the length in an initial numeric header'''
        msg_bytes = msg.encode(_BYTE_ENCODING)
        response_str = _ITEM_ENCODING % (len(msg_bytes), _SEPARATOR, msg)
        return response_str.encode(_BYTE_ENCODING)
        
    def debug(self, msg):
        ''' log a debug msg '''
        pass
