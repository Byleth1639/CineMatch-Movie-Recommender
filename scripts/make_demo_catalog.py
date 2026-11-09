"""Generate the tiny, manually curated offline demo catalog (no ratings)."""
import csv
from pathlib import Path

MOVIES = """
Inception|2010|Action,Sci-Fi,Thriller
Interstellar|2014|Adventure,Drama,Sci-Fi
The Dark Knight|2008|Action,Crime,Drama
The Dark Knight Rises|2012|Action,Crime,Drama
Batman Begins|2005|Action,Crime,Drama
The Prestige|2006|Drama,Mystery,Sci-Fi
Memento|2000|Mystery,Thriller
Dunkirk|2017|Action,Drama,War
Oppenheimer|2023|Drama
Tenet|2020|Action,Sci-Fi,Thriller
The Matrix|1999|Action,Sci-Fi,Thriller
The Matrix Reloaded|2003|Action,Sci-Fi,Thriller
Blade Runner|1982|Sci-Fi,Thriller
Blade Runner 2049|2017|Drama,Sci-Fi,Thriller
Arrival|2016|Drama,Mystery,Sci-Fi
Dune|2021|Adventure,Drama,Sci-Fi
Dune: Part Two|2024|Action,Adventure,Sci-Fi
Ex Machina|2014|Drama,Sci-Fi,Thriller
Her|2013|Drama,Romance,Sci-Fi
The Martian|2015|Adventure,Drama,Sci-Fi
Gravity|2013|Drama,Sci-Fi,Thriller
2001: A Space Odyssey|1968|Adventure,Sci-Fi
Star Wars: A New Hope|1977|Action,Adventure,Sci-Fi
Star Wars: The Empire Strikes Back|1980|Action,Adventure,Sci-Fi
Star Wars: Return of the Jedi|1983|Action,Adventure,Sci-Fi
Rogue One: A Star Wars Story|2016|Action,Adventure,Sci-Fi
Guardians of the Galaxy|2014|Action,Adventure,Comedy,Sci-Fi
Avengers: Infinity War|2018|Action,Adventure,Sci-Fi
Avengers: Endgame|2019|Action,Adventure,Sci-Fi
Iron Man|2008|Action,Adventure,Sci-Fi
Spider-Man: Into the Spider-Verse|2018|Action,Adventure,Animation
Spider-Man: Across the Spider-Verse|2023|Action,Adventure,Animation
Everything Everywhere All at Once|2022|Action,Adventure,Comedy,Sci-Fi
Back to the Future|1985|Adventure,Comedy,Sci-Fi
Jurassic Park|1993|Action,Adventure,Sci-Fi
E.T. the Extra-Terrestrial|1982|Children,Drama,Sci-Fi
The Terminator|1984|Action,Sci-Fi,Thriller
Terminator 2: Judgment Day|1991|Action,Sci-Fi,Thriller
Alien|1979|Horror,Sci-Fi
Aliens|1986|Action,Horror,Sci-Fi
Predator|1987|Action,Horror,Sci-Fi
District 9|2009|Action,Sci-Fi,Thriller
Edge of Tomorrow|2014|Action,Sci-Fi
Minority Report|2002|Action,Crime,Mystery,Sci-Fi
Looper|2012|Action,Crime,Sci-Fi
Children of Men|2006|Adventure,Drama,Sci-Fi
Snowpiercer|2013|Action,Drama,Sci-Fi
The Hunger Games|2012|Action,Adventure,Sci-Fi
Ready Player One|2018|Action,Adventure,Sci-Fi
The Fifth Element|1997|Action,Adventure,Sci-Fi
The Lord of the Rings: The Fellowship of the Ring|2001|Adventure,Fantasy
The Lord of the Rings: The Two Towers|2002|Adventure,Fantasy
The Lord of the Rings: The Return of the King|2003|Adventure,Fantasy
The Hobbit: An Unexpected Journey|2012|Adventure,Fantasy
Harry Potter and the Sorcerer's Stone|2001|Adventure,Children,Fantasy
Harry Potter and the Prisoner of Azkaban|2004|Adventure,Fantasy,Mystery
Harry Potter and the Deathly Hallows: Part 2|2011|Adventure,Fantasy
The Chronicles of Narnia: The Lion, the Witch and the Wardrobe|2005|Adventure,Children,Fantasy
Pirates of the Caribbean: The Curse of the Black Pearl|2003|Action,Adventure,Fantasy
Pan's Labyrinth|2006|Drama,Fantasy,War
The Princess Bride|1987|Adventure,Comedy,Fantasy,Romance
Spirited Away|2001|Adventure,Animation,Fantasy
Howl's Moving Castle|2004|Adventure,Animation,Fantasy,Romance
Princess Mononoke|1997|Action,Adventure,Animation,Fantasy
My Neighbor Totoro|1988|Animation,Children,Fantasy
Kiki's Delivery Service|1989|Animation,Children,Fantasy
Your Name.|2016|Animation,Drama,Fantasy,Romance
A Silent Voice|2016|Animation,Drama,Romance
Weathering with You|2019|Animation,Drama,Fantasy,Romance
Suzume|2022|Adventure,Animation,Fantasy
The Boy and the Heron|2023|Adventure,Animation,Fantasy
WALL-E|2008|Adventure,Animation,Children,Sci-Fi
Inside Out|2015|Adventure,Animation,Comedy,Drama
Inside Out 2|2024|Adventure,Animation,Comedy,Drama
Up|2009|Adventure,Animation,Comedy,Drama
Coco|2017|Adventure,Animation,Drama,Fantasy
Soul|2020|Adventure,Animation,Comedy,Fantasy
Ratatouille|2007|Animation,Children,Comedy
The Incredibles|2004|Action,Adventure,Animation
Toy Story|1995|Adventure,Animation,Children,Comedy
Toy Story 3|2010|Adventure,Animation,Children,Comedy
Finding Nemo|2003|Adventure,Animation,Children
Finding Dory|2016|Adventure,Animation,Comedy
Shrek|2001|Adventure,Animation,Comedy,Fantasy
Kung Fu Panda|2008|Action,Animation,Comedy
Puss in Boots: The Last Wish|2022|Adventure,Animation,Comedy,Fantasy
The Lion King|1994|Adventure,Animation,Drama
Frozen|2013|Adventure,Animation,Fantasy,Musical
Zootopia|2016|Adventure,Animation,Comedy,Crime
Parasite|2019|Comedy,Drama,Thriller
Memories of Murder|2003|Crime,Drama,Mystery,Thriller
The Wailing|2016|Horror,Mystery,Thriller
Oldboy|2003|Action,Drama,Mystery,Thriller
The Handmaiden|2016|Drama,Romance,Thriller
Train to Busan|2016|Action,Horror,Thriller
Minari|2020|Drama
Decision to Leave|2022|Drama,Mystery,Romance
Past Lives|2023|Drama,Romance
The Social Network|2010|Drama
Steve Jobs|2015|Drama
The Imitation Game|2014|Drama,Thriller,War
A Beautiful Mind|2001|Drama,Romance
The Theory of Everything|2014|Drama,Romance
The Pursuit of Happyness|2006|Drama
Good Will Hunting|1997|Drama,Romance
Dead Poets Society|1989|Drama
Whiplash|2014|Drama
La La Land|2016|Comedy,Drama,Musical,Romance
The Greatest Showman|2017|Drama,Musical
Tick, Tick... Boom!|2021|Drama,Musical
A Star Is Born|2018|Drama,Musical,Romance
The Notebook|2004|Drama,Romance
Pride & Prejudice|2005|Drama,Romance
Eternal Sunshine of the Spotless Mind|2004|Drama,Romance,Sci-Fi
Before Sunrise|1995|Drama,Romance
Before Sunset|2004|Drama,Romance
Before Midnight|2013|Drama,Romance
500 Days of Summer|2009|Comedy,Drama,Romance
Crazy Rich Asians|2018|Comedy,Romance
The Big Sick|2017|Comedy,Drama,Romance
Notting Hill|1999|Comedy,Romance
10 Things I Hate About You|1999|Comedy,Romance
The Devil Wears Prada|2006|Comedy,Drama
Legally Blonde|2001|Comedy,Romance
Mean Girls|2004|Comedy
Superbad|2007|Comedy
The Hangover|2009|Comedy
Game Night|2018|Action,Comedy,Crime
Knives Out|2019|Comedy,Crime,Mystery
Glass Onion: A Knives Out Mystery|2022|Comedy,Crime,Mystery
The Grand Budapest Hotel|2014|Comedy,Drama
The Royal Tenenbaums|2001|Comedy,Drama
Jojo Rabbit|2019|Comedy,Drama,War
Little Miss Sunshine|2006|Comedy,Drama
The Truman Show|1998|Comedy,Drama,Sci-Fi
The Secret Life of Walter Mitty|2013|Adventure,Comedy,Drama
Forrest Gump|1994|Comedy,Drama,Romance
The Shawshank Redemption|1994|Crime,Drama
The Green Mile|1999|Crime,Drama,Fantasy
The Godfather|1972|Crime,Drama
The Godfather Part II|1974|Crime,Drama
Goodfellas|1990|Crime,Drama
The Departed|2006|Crime,Drama,Thriller
Heat|1995|Action,Crime,Drama
The Irishman|2019|Crime,Drama
The Wolf of Wall Street|2013|Comedy,Crime,Drama
Catch Me If You Can|2002|Crime,Drama
Ocean's Eleven|2001|Crime,Thriller
Pulp Fiction|1994|Comedy,Crime,Drama
Reservoir Dogs|1992|Crime,Mystery,Thriller
Django Unchained|2012|Drama,Western
Inglourious Basterds|2009|Action,Drama,War
Once Upon a Time in Hollywood|2019|Comedy,Drama
Kill Bill: Vol. 1|2003|Action,Crime,Thriller
Kill Bill: Vol. 2|2004|Action,Crime,Thriller
Fight Club|1999|Action,Crime,Drama,Thriller
Se7en|1995|Crime,Mystery,Thriller
Zodiac|2007|Crime,Drama,Mystery,Thriller
Gone Girl|2014|Drama,Mystery,Thriller
Prisoners|2013|Crime,Drama,Mystery,Thriller
Shutter Island|2010|Drama,Mystery,Thriller
The Silence of the Lambs|1991|Crime,Horror,Thriller
The Sixth Sense|1999|Drama,Horror,Mystery
Get Out|2017|Horror,Mystery,Thriller
Us|2019|Horror,Mystery,Thriller
Nope|2022|Horror,Mystery,Sci-Fi
A Quiet Place|2018|Drama,Horror,Sci-Fi,Thriller
Hereditary|2018|Drama,Horror,Mystery
Midsommar|2019|Drama,Horror,Mystery
The Conjuring|2013|Horror,Mystery,Thriller
It|2017|Drama,Horror,Thriller
The Babadook|2014|Drama,Horror,Thriller
The Witch|2015|Horror,Mystery
The Shining|1980|Horror
Doctor Sleep|2019|Drama,Horror
Scream|1996|Comedy,Horror,Mystery
The Exorcist|1973|Horror
Jaws|1975|Adventure,Horror,Thriller
Black Swan|2010|Drama,Thriller
Nightcrawler|2014|Crime,Drama,Thriller
Drive|2011|Action,Crime,Drama
Baby Driver|2017|Action,Crime,Music,Thriller
John Wick|2014|Action,Crime,Thriller
John Wick: Chapter 4|2023|Action,Crime,Thriller
Mission: Impossible – Fallout|2018|Action,Adventure,Thriller
Top Gun: Maverick|2022|Action,Drama
Mad Max: Fury Road|2015|Action,Adventure,Sci-Fi
Furiosa: A Mad Max Saga|2024|Action,Adventure,Sci-Fi
The Bourne Identity|2002|Action,Mystery,Thriller
Casino Royale|2006|Action,Adventure,Thriller
Skyfall|2012|Action,Adventure,Thriller
The Batman|2022|Action,Crime,Drama
Joker|2019|Crime,Drama,Thriller
Logan|2017|Action,Drama,Sci-Fi
The Avengers|2012|Action,Adventure,Sci-Fi
Black Panther|2018|Action,Adventure,Sci-Fi
Wonder Woman|2017|Action,Adventure,Fantasy
1917|2019|Drama,War
Saving Private Ryan|1998|Action,Drama,War
Schindler's List|1993|Drama,War
The Pianist|2002|Drama,War
All Quiet on the Western Front|2022|Action,Drama,War
The Hurt Locker|2008|Drama,Thriller,War
Apocalypse Now|1979|Drama,War
The Revenant|2015|Adventure,Drama,Western
No Country for Old Men|2007|Crime,Drama,Thriller,Western
There Will Be Blood|2007|Drama
The Power of the Dog|2021|Drama,Western
The Hateful Eight|2015|Mystery,Thriller,Western
The Good, the Bad and the Ugly|1966|Adventure,Western
12 Angry Men|1957|Drama
Citizen Kane|1941|Drama,Mystery
Casablanca|1942|Drama,Romance,War
Rear Window|1954|Mystery,Thriller
Vertigo|1958|Drama,Mystery,Romance,Thriller
Psycho|1960|Horror,Mystery,Thriller
One Flew Over the Cuckoo's Nest|1975|Drama
Rocky|1976|Drama
Raging Bull|1980|Drama
The King's Speech|2010|Drama
The Shape of Water|2017|Drama,Fantasy,Romance
The Favourite|2018|Comedy,Drama
Poor Things|2023|Comedy,Drama,Romance,Sci-Fi
Barbie|2023|Adventure,Comedy,Fantasy
The Holdovers|2023|Comedy,Drama
American Fiction|2023|Comedy,Drama
Anatomy of a Fall|2023|Crime,Drama,Thriller
The Zone of Interest|2023|Drama,War
The Boy in the Striped Pajamas|2008|Drama,War
Hidden Figures|2016|Drama
The Big Short|2015|Comedy,Drama
Moneyball|2011|Drama
Ford v Ferrari|2019|Action,Drama
Rush|2013|Action,Drama
The Iron Claw|2023|Drama
The Wrestler|2008|Drama
Creed|2015|Drama
Remember the Titans|2000|Drama
The Blind Side|2009|Drama
The Intouchables|2011|Comedy,Drama
Amélie|2001|Comedy,Romance
The Lives of Others|2006|Drama,Thriller
City of God|2002|Crime,Drama
Roma|2018|Drama
The Farewell|2019|Comedy,Drama
The Florida Project|2017|Drama
Moonlight|2016|Drama
Lady Bird|2017|Comedy,Drama
Little Women|2019|Drama,Romance
Marriage Story|2019|Drama
Manchester by the Sea|2016|Drama
Aftersun|2022|Drama
The Whale|2022|Drama
The Menu|2022|Comedy,Horror,Thriller
Triangle of Sadness|2022|Comedy,Drama
The Lobster|2015|Comedy,Drama,Romance,Sci-Fi
The Killing of a Sacred Deer|2017|Drama,Horror,Mystery
"""

out = Path(__file__).resolve().parents[1] / 'data' / 'demo_movies.csv'
with out.open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['movieId', 'title', 'genres'])
    for i, line in enumerate(MOVIES.strip().splitlines(), 1):
        title, year, genre_list = line.split('|')
        w.writerow([i, f'{title} ({year})', '|'.join(genre_list.split(','))])
print(f'Created {i} real movie titles with manually curated metadata, no ratings: {out}')
