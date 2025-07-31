# TODO:
# Songs that have indented chords in the first line need to be manually updated
# Songs with an [Intro] need to have this manually added
import re
import html
import subprocess
import json
import os

def fetch_url_content(url: str) -> str | None:
    try:
        result = subprocess.run(['curl', '-s', url], capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else None
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return None

def extract_and_clean_title_and_artist(content: str) -> tuple[str | None, str | None]:
    # Extract <title> tag text
    match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
    if not match:
        return None, None
    title = match.group(1)

    # Remove trailing stuff and "chords" word, normalize spaces
    title = re.sub(r'\s*@.*$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\bchords\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+', ' ', title).strip()

    # Split by "by" for song and artist (case insensitive)
    parts = re.split(r'\s+by\s+', title, flags=re.IGNORECASE)
    song = parts[0].strip() if len(parts) > 0 else None
    artist = parts[1].strip() if len(parts) > 1 else None
    return song, artist

def extract_and_clean_section(raw_content: str) -> str | None:
    # Find first [ch]
    start_idx = raw_content.find('[ch]')
    if start_idx == -1:
        return None

    # Find first &quot after start_idx
    end_idx = raw_content.find('&quot', start_idx)
    if end_idx == -1:
        end_idx = len(raw_content)

    # Extract substring between start_idx and end_idx
    section = raw_content[start_idx:end_idx]

    # Unescape HTML entities and normalize newlines
    section = html.unescape(section)
    section = section.replace('\\r\\n', '\n').replace('\r\n', '\n')

    # Remove [tab], [/tab], [ch], [/ch] tags
    section = re.sub(r'\[/?tab\]', '', section)
    section = re.sub(r'\[ch\]', '<strong>', section)
    section = re.sub(r'\[/ch\]', '</strong>', section)

    # Strip trailing whitespace from lines but keep structure
    lines = [line.rstrip() for line in section.splitlines()]

    # Remove blank lines that come directly after lines ending with ']'
    cleaned_lines = []
    skip_next_blank = False
    for line in lines:
        if skip_next_blank and line.strip() == '':
            # skip this blank line
            continue
        cleaned_lines.append(line)
        # Set flag if current line ends with ']'
        skip_next_blank = line.rstrip().endswith(']')

    cleaned = '\n'.join(cleaned_lines)

    # Also ensure max 1 blank line anywhere (optional)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned

def load_songs(filepath: str) -> list:
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_songs(filepath: str, songs: list) -> None:
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(songs, f, ensure_ascii=False, indent=2)

def main():
    url = input("Enter URL: ")
    html_content = fetch_url_content(url)

    if not html_content:
        print("Failed to fetch URL content.")
        return

    song_title, artist_name = extract_and_clean_title_and_artist(html_content)
    if not song_title or not artist_name:
        print("Missing title or artist in HTML content.")
        return
    
    song_title = song_title.title()
    artist_name = artist_name.title()

    body_text = extract_and_clean_section(html_content)
    if not body_text:
        print("Failed to extract tab section from content.")
        return

    songs_file = 'songs.json'
    songs_list = load_songs(songs_file)

    # Case-insensitive search for existing song entry
    found_index = next(
        (i for i, s in enumerate(songs_list)
         if s.get("title", "").lower() == song_title.lower() and s.get("artist", "").lower() == artist_name.lower()),
        None
    )

    new_entry = {
        "title": song_title,
        "artist": artist_name,
        "body": body_text
    }

    if found_index is not None:
        songs_list[found_index] = new_entry
        print(f"Overwrote existing entry for '{song_title}' by '{artist_name}'.")
    else:
        songs_list.append(new_entry)
        print(f"Appended new entry for '{song_title}' by '{artist_name}'.")

    save_songs(songs_file, songs_list)

if __name__ == "__main__":
    main()