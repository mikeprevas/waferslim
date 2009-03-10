''' Example code for demonstrating value comparisons and symbols -- 
based on http://fitnesse.org/FitNesse.SliM.ValueComparisons
and http://fitnesse.org/FitNesse.SliM.SymbolsInTables.
Hopefully this example demonstrates that there's no extra work required for
your own code if you wish to use value comparisons or symbols.
'''
from waferslim.converters import convert_arg

class SomeDecisionTable:
    ''' Class to be the system under test in fitnesse '''
    
    @convert_arg(to_type=int)
    def setInput(self, int_value):
        ''' Takes the value from the "input" column of the table.
        The convert_arg decorator ensures that the "int_value" param to the
        method is indeed of type "int".'''
        self._int_value = int_value
        
    def output(self):
        ''' Provides the value back to the "output" column of the table.
        Note that there is nothing in this code about value comparisons
        or symbols: all of that is taken care of by waferslim and fitnesse.'''
        if self._int_value % 2 == 0:
            return (self._int_value * 2)
        return self._int_value + 1
        