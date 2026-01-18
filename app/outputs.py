""" 
Outputs - Salida de resultados a terminal
==========================================
Maneja la salida de resultados del análisis a la terminal.

Flujo: strategies.py → Output.to_cli() → Terminal
"""

import numpy as np
import structlog


class Output():
    """
    Maneja la salida de resultados a la terminal.
    
    Nota: Métodos to_csv y to_json eliminados (deprecados 2026-01-18).
    """

    def __init__(self):
        self.logger = structlog.get_logger()
        self.dispatcher = {
            'cli': self.to_cli
        }

    def to_cli(self, results, market_pair):
        """Creates the message to output to the CLI

        Args:
            market_pair (str): Market pair that this message relates to.
            results (dict): The result of the completed analysis to output.

        Returns:
            str: Completed cli message
        """

        normal_colour = '\u001b[0m'
        hot_colour = '\u001b[31m'
        cold_colour = '\u001b[36m'

        output = "{}:\t\n".format(market_pair)
        for indicator_type in results:
            output += '\n{}:\t'.format(indicator_type)
            for indicator in results[indicator_type]:
                for i, analysis in enumerate(results[indicator_type][indicator]):
                    # Skip si el resultado es un string (error) o está vacío
                    if isinstance(analysis['result'], str) or analysis['result'].shape[0] == 0:
                        self.logger.info('No results for %s #%s', indicator, i)
                        continue

                    colour_code = normal_colour

                    if 'is_hot' in analysis['result'].iloc[-1]:
                        if analysis['result'].iloc[-1]['is_hot']:
                            colour_code = hot_colour

                    if 'is_cold' in analysis['result'].iloc[-1]:
                        if analysis['result'].iloc[-1]['is_cold']:
                            colour_code = cold_colour

                    if indicator_type == 'crossovers':
                        key_signal = '{}_{}'.format(
                            analysis['config']['key_signal'],
                            analysis['config']['key_indicator_index']
                        )

                        key_value = analysis['result'].iloc[-1][key_signal]

                        crossed_signal = '{}_{}'.format(
                            analysis['config']['crossed_signal'],
                            analysis['config']['crossed_indicator_index']
                        )

                        crossed_value = analysis['result'].iloc[-1][crossed_signal]

                        if isinstance(key_value, float):
                            key_value = format(key_value, '.8f')

                        if isinstance(crossed_value, float):
                            crossed_value = format(crossed_value, '.8f')

                        formatted_string = '{}/{}'.format(
                            key_value, crossed_value)
                        output += "{}{}: {}{} \t".format(
                            colour_code,
                            '{} #{}'.format(indicator, i),
                            formatted_string,
                            normal_colour
                        )
                    else:
                        # Skip si no hay configuración de signal
                        if 'signal' not in analysis['config']:
                            continue
                        
                        formatted_values = list()
                        for signal in analysis['config']['signal']:
                            value = analysis['result'].iloc[-1][signal]
                            if isinstance(value, float) or isinstance(value, np.int32):
                                formatted_values.append(format(value, '.8f'))
                            else:
                                formatted_values.append(value)
                            formatted_string = '/'.join(formatted_values)

                        output += "{}{}: {}{} \t".format(
                            colour_code,
                            '{} #{}'.format(indicator, i),
                            formatted_string,
                            normal_colour
                        )

        output += '\n\n'
        return output
