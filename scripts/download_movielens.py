"""Download the GroupLens MovieLens latest-small dataset into data/.

Review https://grouplens.org/datasets/movielens/ and its license first.
The contents are deliberately not included in the CineMatch repository.
"""
from pathlib import Path
import io
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data"
URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"


def main() -> None:
    print("MovieLens data license: https://files.grouplens.org/datasets/movielens/ml-latest-small-README.html")
    print("This dataset is for non-commercial research/education; check all usage conditions.")
    if "--accept-license" not in sys.argv:
        print("If you accept its terms, rerun with: python scripts/download_movielens.py --accept-license")
        sys.exit(2)
    print("Downloading official MovieLens latest-small ...")
    request = urllib.request.Request(URL, headers={"User-Agent": "CineMatch-Educational/1.0"})
    with urllib.request.urlopen(request, timeout=40) as response:
        data = response.read()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        expected = {"ml-latest-small/movies.csv", "ml-latest-small/ratings.csv"}
        if not expected.issubset(archive.namelist()):
            raise ValueError("Downloaded archive does not have the expected files")
        for member in archive.infolist():
            file_path = Path(member.filename)
            if file_path.parts[0] != "ml-latest-small" or ".." in file_path.parts:
                raise ValueError("Unexpected path in archive")
        archive.extractall(DEST)
    print("Ready! Restart the server to enable collaborative filtering with real ratings.")


if __name__ == "__main__":
    main()
