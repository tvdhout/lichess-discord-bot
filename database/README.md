## Database

My database contains a table "puzzles" with all the lichess puzzles to date. Puzzles are stored as follows.

| puzzle_id | rating | color | answers                                             | follow_up                            |
|-----------|--------|-------|-----------------------------------------------------|--------------------------------------|
| 56        | 1728   | black | ['Qe5+', 'Rf1+', 'Qe1#']                            | ['Kg1', 'Kxf1']                      |
| 57        | 1653   | black | ['Qd5+', 'Re2+', 'Rexf2+', 'Rxf2+', 'Qf3+', 'Rh2#'] | ['Kh2', 'Rf2', 'Qxf2', 'Kg3', 'Kh4'] |
| 58        | 1233   | black | ['Bxg5']                                            | []                                   |

* puzzle_id is the puzzle identifier (e.g. https://lichess.org/training/56 is the puzzle with puzzle_id 56)
* rating is the puzzle's difficulty rating 
* color is the color to play
* answers is the correct moves the user should play (the first correct line if multiple exist)
* follow_up the response from the opponent to those moves.

The table can be downloaded [as csv](/database/puzzles.csv).
