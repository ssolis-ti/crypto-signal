""" Utilities for notifiers
"""

import structlog

class NotifierUtils():
    """ Utilities for notifiers
    """

    def __init__(self):
        self.logger = structlog.get_logger()


    def chunk_message(self, message, max_message_size):
        """ Chunks message so that it meets max size of integration.

        Args:
            message (str): The message to chunk.
            max_message_size (int): The max message length for the chunks.

        Returns:
            list: The chunked message.
        """

        chunked_message = list()
        if len(message) > max_message_size:
            chunk = ''

            for message_part in message.splitlines(keepends=True):
                # Una linea sola mas larga que el limite (p. ej. un resumen de LLM sin
                # saltos) se parte a mano: antes se descartaba entera y la alerta se perdia.
                if len(message_part) > max_message_size:
                    if chunk:
                        chunked_message.append(chunk)
                        chunk = ''
                    for start in range(0, len(message_part), max_message_size):
                        piece = message_part[start:start + max_message_size]
                        if len(piece) == max_message_size:
                            chunked_message.append(piece)
                        else:
                            chunk = piece
                    continue

                if len(chunk) + len(message_part) > max_message_size:
                    chunked_message.append(chunk)
                    chunk = ''

                chunk += message_part

            # Flush del ultimo chunk: sin esto se perdia la cola de todo mensaje > limite.
            if chunk:
                chunked_message.append(chunk)
        else:
            chunked_message.append(message)

        return chunked_message