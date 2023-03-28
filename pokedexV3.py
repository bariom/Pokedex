import sys
import pokebase as pb
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QScrollArea, QGridLayout, QDialog, QFrame, QLineEdit, QMessageBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import mysql.connector
from mysql.connector import Error
from io import BytesIO


class PokemonInfoApp(QWidget):
    def __init__(self, num_pokemon=1000, per_page=10):
        super().__init__()
        self.num_pokemon = num_pokemon
        self.per_page = per_page
        self.current_page = 0
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Pokémon Info')

        self.layout = QVBoxLayout()

        self.grid_layout = QGridLayout()
        self.update_grid()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setLayout(self.grid_layout)
        scroll.setWidget(content)

        self.prev_button = QPushButton('Previous')
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button = QPushButton('Next')
        self.next_button.clicked.connect(self.next_page)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.prev_button)
        buttons_layout.addWidget(self.next_button)

        # Add search bar
        search_layout = QHBoxLayout()
        self.search_field = QLineEdit(self)
        self.search_field.setPlaceholderText("Enter Pokémon name or ID")
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_pokemon)
        search_layout.addWidget(self.search_field)
        search_layout.addWidget(self.search_button)

        outer_layout = QVBoxLayout()
        outer_layout.addLayout(search_layout)
        outer_layout.addWidget(scroll)
        outer_layout.addLayout(buttons_layout)
        self.setLayout(outer_layout)

        self.setGeometry(300, 300, 800, 950)
        self.update_buttons()

    # New search_pokemon method
    def search_pokemon(self):
        search_name = None
        search_input = self.search_field.text().strip()
        if not search_input:
            return

        try:
            # Check if input is a valid number (ID)
            search_id = int(search_input)
        except ValueError:
            # If not a number, treat it as a name
            search_id = None
            search_name = search_input.lower()

        found = False
        for i in range(self.num_pokemon):
            index = i
            pokemon = self.get_pokemon_info(index + 1)
            if search_id and pokemon["id"] == search_id:
                found = True
            elif search_name and pokemon["name"].lower() == search_name:
                found = True

            if found:
                self.current_page = index // self.per_page
                self.clear_grid()
                self.update_grid()
                self.update_buttons()
                break

        if not found:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Not Found")
            msg.setInformativeText("Pokémon not found. Please try again.")
            msg.setWindowTitle("Not Found")
            msg.exec_()

    def update_grid(self):
        for i in range(self.per_page):
            index = self.current_page * self.per_page + i
            if index < self.num_pokemon:
                pokemon = self.get_pokemon_info(index + 1)
                hbox = QHBoxLayout()

                # Display Pokémon image
                pixmap = QPixmap()
                pixmap.loadFromData(pokemon["image"])
                image_label = QLabel(self)
                image_label.setPixmap(pixmap)
                hbox.addWidget(image_label)

                # Display Pokémon information
                info_label = QLabel(self)
                info_text = f"ID: {pokemon['id']}\nName: {pokemon['name']}\nTypes: {pokemon['type']}\nAbilities: {pokemon['abilities']}\nHeight: {pokemon['height']}\nWeight: {pokemon['weight']}"
                info_label.setText(info_text)
                hbox.addWidget(info_label)

                # Connect the mousePressEvent signal of the image_label to the show_details method
                image_label.pokemon_info = pokemon
                image_label.setCursor(Qt.PointingHandCursor)
                image_label.mousePressEvent = lambda event, label=image_label: self.show_details(label)

                self.grid_layout.addLayout(hbox, i // 2, i % 2)

    def show_details(self, label):
        # Get the Pokémon info from the clicked image_label
        pokemon_info = label.pokemon_info

        # Create and show the PokemonDetails dialog
        dialog = PokemonDetails(self, pokemon_info=pokemon_info)
        dialog.exec_()

    def get_pokemon_info(self, pokemon_id):
        try:
            # Cerca il Pokémon nel database
            mydb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="Baro0014!",
                database="PokemonDB"
            )
            cursor = mydb.cursor()

            sql = "SELECT * FROM pokemon WHERE id = %s"
            values = (pokemon_id,)
            cursor.execute(sql, values)
            result = cursor.fetchone()

            if result is not None:
                # Se il Pokémon è presente nel database, restituisci le informazioni salvate
                pokemon = {
                    "id": result[0],
                    "name": result[1],
                    "type": result[2],
                    "abilities": result[3],
                    "height": result[4],
                    "weight": result[5],
                    "image": result[6]
                }
            else:
                # Se il Pokémon non è presente nel database, cerca le informazioni tramite le API
                pokemon = self.get_pokemon_info_from_api(pokemon_id)

                try:
                    # Salva i dati del nuovo Pokémon nel database
                    sql = "INSERT INTO pokemon (id, name, type, abilities, height, weight, image) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    values = (pokemon["id"], pokemon["name"], pokemon["type"], pokemon["abilities"], pokemon["height"],
                              pokemon["weight"], pokemon["image"])
                    cursor.execute(sql, values)
                    mydb.commit()
                except mysql.connector.Error as error:
                    # Gestione dell'errore di salvataggio dei dati nel database
                    print(f"Error saving data to MySQL table: {error}")

            # Chiusura della connessione al database
            mydb.close()

            return pokemon


        except mysql.connector.Error as error:

            # Gestione dell'errore di connessione al database

            print(f"Error connecting to MySQL database: {error}")

    def get_pokemon_info_from_api(self, pokemon_id):

        # Ottiene le informazioni del Pokémon dall'API

        response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}")

        pokemon_data = response.json()

        # Estrae le informazioni del Pokémon dal JSON restituito dall'API

        pokemon = {
            "id": pokemon_data["id"],
            "name": pokemon_data["name"].capitalize(),
            "type": ", ".join([t["type"]["name"].capitalize() for t in pokemon_data["types"]]),
            "abilities": ", ".join([a["ability"]["name"].capitalize() for a in pokemon_data["abilities"]]),
            "height": pokemon_data["height"],
            "weight": pokemon_data["weight"],
            "image": requests.get(pokemon_data["sprites"]["front_default"]).content,
        }
        return pokemon

    def clear_grid(self):

        for i in reversed(range(self.grid_layout.count())):

            layout_item = self.grid_layout.itemAt(i)

            while layout_item.count():
                item = layout_item.takeAt(0)

                item.widget().setParent(None)

            self.grid_layout.removeItem(layout_item)

    def update_buttons(self):

        self.prev_button.setEnabled(self.current_page > 0)

        self.next_button.setEnabled((self.current_page + 1) * self.per_page < self.num_pokemon)

    def prev_page(self):

        if self.current_page > 0:
            self.current_page -= 1

            self.clear_grid()

            self.update_grid()

            self.update_buttons()

    def next_page(self):

        if (self.current_page + 1) * self.per_page < self.num_pokemon:
            self.current_page += 1

            self.clear_grid()

            self.update_grid()

            self.update_buttons()



class PokemonDetails(QDialog):
    def __init__(self, parent=None, pokemon_info=None):
        super().__init__(parent)
        self.pokemon_info = pokemon_info
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Pokémon Details')

        main_layout = QVBoxLayout()
        buttons_layout = QHBoxLayout()

        # Card frame
        card_frame = QFrame(self)
        card_frame.setObjectName("CardFrame")
        card_frame.setFrameShape(QFrame.StyledPanel)
        card_frame.setFrameShadow(QFrame.Raised)
        card_layout = QVBoxLayout()

        # Fetch high-resolution image
        response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{self.pokemon_info['id']}")
        pokemon_data = response.json()
        high_res_image_url = pokemon_data["sprites"]["other"]["official-artwork"]["front_default"]
        high_res_image = requests.get(high_res_image_url).content

        # Extract base experience and stats from the API data
        base_experience = pokemon_data['base_experience']
        stats = {stat["stat"]["name"].capitalize(): stat["base_stat"] for stat in pokemon_data["stats"]}

        # Display Pokémon image
        pixmap = QPixmap()
        pixmap.loadFromData(high_res_image)
        image_label = QLabel(self)
        image_label.setPixmap(pixmap)
        card_layout.addWidget(image_label, alignment=Qt.AlignCenter)

        # Display Pokémon information
        info_label = QLabel(self)
        info_text = f"<b>ID:</b> {self.pokemon_info['id']}<br><b>Name:</b> {self.pokemon_info['name']}<br><b>Types:</b> {self.pokemon_info['type']}<br><b>Abilities:</b> {self.pokemon_info['abilities']}<br><b>Height:</b> {self.pokemon_info['height']}<br><b>Weight:</b> {self.pokemon_info['weight']}<br><b>Base Experience:</b> {base_experience}<br><b>Stats:</b><br>"
        info_text += "<br>".join([f"{stat}: {value}" for stat, value in stats.items()])
        info_label.setText(info_text)
        card_layout.addWidget(info_label, alignment=Qt.AlignCenter)

        card_frame.setLayout(card_layout)
        main_layout.addWidget(card_frame, alignment=Qt.AlignCenter)

#        self.id_field = QLineEdit(self)
#        self.id_field.setPlaceholderText("Enter Pokémon ID")

#        self.go_button = QPushButton("Go")
#        self.go_button.clicked.connect(self.go_to_pokemon_id)

#        buttons_layout.addWidget(self.id_field)
#        buttons_layout.addWidget(self.go_button)


        self.setLayout(main_layout)

        # Apply styles
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
            }
            QFrame#CardFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                width: 300px;
                min-height: 400px;
            }
            QLabel {
                color: #333;
            }
        """)

    def go_to_pokemon_id(self):
        try:
            pokemon_id = int(self.id_field.text())
            if 1 <= pokemon_id <= self.num_pokemon:
                # Calculate the page index and grid position for the specified Pokémon ID
                page = (pokemon_id - 1) // self.per_page
                self.current_page = page

                self.clear_grid()
                self.update_grid()
                self.update_buttons()

                # Open the Pokémon Details dialog for the specified Pokémon ID
                pokemon_info = self.get_pokemon_info(pokemon_id)
                dialog = PokemonDetails(self, pokemon_info=pokemon_info)
                dialog.exec_()

            else:
                # Show an error message if the Pokémon ID is not within the valid range
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("Error")
                msg.setInformativeText("Please enter a valid Pokémon ID.")
                msg.setWindowTitle("Error")
                msg.exec_()

        except ValueError:
            # Show an error message if the input is not a valid number
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText("Please enter a valid number.")
            msg.setWindowTitle("Error")
            msg.exec_()

def main():
    app = QApplication(sys.argv)

    ex = PokemonInfoApp()

    ex.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
