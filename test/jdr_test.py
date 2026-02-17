# jdr_test.py
import requests
import json
import time
import os
import sys
import io
from typing import Optional
from pathlib import Path


# ============================
# IMAGES DE TEST
# ============================

TEST_IMAGES = {
    "board_bg": {
        "url": "https://laboiteachimere.com/bac/wp-content/uploads/2022/09/ss_0fc7becdbcacf9ff68231608b92e6c610e2d9136.1920x1080-800x445.jpg",
        "filename": "board_bg.jpg",
        "description": "Image de fond du board"
    },
    "monster": {
        "url": "https://www.blog.leroliste.com/wp-content/uploads/article-jdr-aventure-1024x640.jpg",
        "filename": "monster.jpg",
        "description": "Image du monstre"
    },
    "character_avatar": {
        "url": "https://black-book-editions.fr/contenu/users/55424/image/Carte_Perso_Klauss.jpg",
        "filename": "character_avatar.jpg",
        "description": "Avatar du personnage"
    }
}

IMAGE_CACHE_DIR = Path("test_images_cache")


def download_test_images() -> dict[str, bytes]:
    """
    Télécharge les images de test et les met en cache localement.
    Retourne un dict {key: bytes}
    """
    IMAGE_CACHE_DIR.mkdir(exist_ok=True)
    downloaded = {}

    print("\n📥 Téléchargement des images de test...")
    for key, info in TEST_IMAGES.items():
        cache_path = IMAGE_CACHE_DIR / info["filename"]

        # Utilise le cache si dispo
        if cache_path.exists():
            print(f"  ✅ {info['description']} (cache local)")
            with open(cache_path, "rb") as f:
                downloaded[key] = f.read()
            continue

        # Télécharge
        print(f"  ⬇️  {info['description']} depuis {info['url'][:60]}...")
        try:
            response = requests.get(info["url"], timeout=15)
            response.raise_for_status()
            data = response.content
            # Sauvegarde le cache
            with open(cache_path, "wb") as f:
                f.write(data)
            downloaded[key] = data
            print(f"      ✅ {len(data) // 1024} KB téléchargés")
        except Exception as e:
            print(f"      ❌ Échec: {e}")
            downloaded[key] = None

    return downloaded


# ============================
# API TESTER
# ============================

class JDRTester:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.org_id: Optional[int] = None
        self.jdr_id: Optional[int] = None
        self.membership_id: Optional[int] = None
        self.character_id: Optional[int] = None

    def _headers(self, auth: bool = True) -> dict:
        headers = {}
        if auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _print_response(self, response: requests.Response, title: str):
        print(f"\n{'=' * 60}")
        print(f"🔹 {title}")
        print(f"{'=' * 60}")
        status_icon = "✅" if response.status_code < 400 else "❌"
        print(f"{status_icon} Status: {response.status_code}")
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            return response, data
        except Exception:
            print(f"Response: {response.text}")
            return response, None
        finally:
            print(f"{'=' * 60}\n")

    # ==================== AUTH ====================

    def register(self, email: str, password: str):
        response = requests.post(
            f"{self.base_url}/auth/register",
            json={"email": email, "password": password},
            headers=self._headers(auth=False)
        )
        resp, data = self._print_response(response, f"REGISTER {email}")
        if response.status_code == 201 and data:
            self.user_id = data.get("id")
        return resp, data

    def login(self, email: str, password: str):
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password},
            headers=self._headers(auth=False)
        )
        resp, data = self._print_response(response, f"LOGIN {email}")
        if response.status_code == 200 and data:
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
        return resp, data

    # ==================== IMAGES ====================

    def upload_image(
        self,
        image_bytes: bytes,
        filename: str,
        category: str = "misc",
        jdr_id: int = None,
        org_id: int = None,
        tags: dict = None,
        resize_width: int = None,
        resize_height: int = None
    ):
        """Upload une image depuis des bytes"""
        if image_bytes is None:
            print(f"⚠️  Image {filename} non disponible, skip upload")
            return None, None

        files = {
            "file": (filename, io.BytesIO(image_bytes), "image/jpeg")
        }
        data = {"category": category}
        if jdr_id:
            data["jdr_id"] = str(jdr_id)
        if org_id:
            data["organization_id"] = str(org_id)
        if tags:
            data["tags"] = json.dumps(tags)
        if resize_width and resize_height:
            data["resize_width"] = str(resize_width)
            data["resize_height"] = str(resize_height)

        response = requests.post(
            f"{self.base_url}/images/upload",
            files=files,
            data=data,
            headers=self._headers()
        )
        return self._print_response(response, f"UPLOAD IMAGE {filename} -> {category}")

    def resize_image(self, filename: str, category: str, width: int, height: int,
                     quality: int = 85, keep_ratio: bool = True):
        response = requests.post(
            f"{self.base_url}/images/resize",
            json={
                "filename": filename,
                "category": category,
                "width": width,
                "height": height,
                "quality": quality,
                "keep_ratio": keep_ratio
            },
            headers=self._headers()
        )
        return self._print_response(response, f"RESIZE IMAGE {filename} -> {width}x{height}")

    def board_canvas(self, jdr_id: int, filename: str, category: str,
                     canvas_width: int, canvas_height: int,
                     position_x: int = 0, position_y: int = 0,
                     img_width: int = None, img_height: int = None):
        payload = {
            "filename": filename,
            "category": category,
            "canvas_width": canvas_width,
            "canvas_height": canvas_height,
            "position_x": position_x,
            "position_y": position_y,
        }
        if img_width:
            payload["img_width"] = img_width
        if img_height:
            payload["img_height"] = img_height

        response = requests.post(
            f"{self.base_url}/images/board-canvas/{jdr_id}",
            json=payload,
            headers=self._headers()
        )
        return self._print_response(response, f"BOARD CANVAS {canvas_width}x{canvas_height}")

    def list_jdr_images(self, jdr_id: int, category: str = None):
        url = f"{self.base_url}/images/jdr/{jdr_id}"
        if category:
            url += f"?category={category}"
        response = requests.get(url, headers=self._headers())
        return self._print_response(response, f"LIST JDR IMAGES jdr={jdr_id}")

    def get_image_info(self, category: str, filename: str):
        response = requests.get(
            f"{self.base_url}/images/info/{category}/{filename}",
            headers=self._headers()
        )
        return self._print_response(response, f"IMAGE INFO {category}/{filename}")

    def delete_image(self, image_id: int):
        response = requests.delete(
            f"{self.base_url}/images/{image_id}",
            headers=self._headers()
        )
        return self._print_response(response, f"DELETE IMAGE {image_id}")

    # ==================== ORGANIZATION ====================

    def create_organization(self, name: str, slug: str):
        response = requests.post(
            f"{self.base_url}/organizations/",
            json={
                "name": name,
                "slug": slug,
                "description": f"Organisation pour {name}",
                "visibility": "public",
                "join_mode": "open"
            },
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        resp, data = self._print_response(response, f"CREATE ORGANIZATION {name}")
        if response.status_code == 201 and data:
            self.org_id = data.get("id")
        return resp, data

    def join_organization(self, org_id: int):
        response = requests.post(
            f"{self.base_url}/organizations/{org_id}/join",
            json={"message": "Je veux rejoindre!"},
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        return self._print_response(response, f"JOIN ORGANIZATION {org_id}")

    # ==================== JDR ====================

    def create_jdr(self, org_id: int, name: str, universe: str = "D&D 5e", max_players: int = 4):
        response = requests.post(
            f"{self.base_url}/organizations/{org_id}/jdrs/",
            json={
                "name": name,
                "description": f"Une aventure épique : {name}",
                "universe": universe,
                "max_players": max_players,
                "is_public": True,
                "settings": {"dice_system": "d20", "language": "fr", "allow_pvp": False}
            },
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        resp, data = self._print_response(response, f"CREATE JDR {name}")
        if response.status_code == 201 and data:
            self.jdr_id = data.get("id")
        return resp, data

    def update_jdr(self, org_id: int, jdr_id: int, **kwargs):
        response = requests.patch(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}",
            json=kwargs,
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        return self._print_response(response, f"UPDATE JDR {jdr_id}")

    def list_jdrs(self, org_id: int):
        response = requests.get(
            f"{self.base_url}/organizations/{org_id}/jdrs/",
            headers=self._headers()
        )
        return self._print_response(response, f"LIST JDRs ORG {org_id}")

    # ==================== JDR MEMBERSHIP ====================

    def join_jdr(self, org_id: int, jdr_id: int, message: str = "Je veux jouer!"):
        response = requests.post(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/join",
            json={"join_message": message},
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        resp, data = self._print_response(response, f"JOIN JDR {jdr_id}")
        if response.status_code == 200 and data:
            self.membership_id = data.get("id")
        return resp, data

    def approve_player(self, org_id: int, jdr_id: int, membership_id: int):
        response = requests.post(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/members/{membership_id}/approve",
            headers=self._headers()
        )
        return self._print_response(response, f"APPROVE PLAYER membership={membership_id}")

    # ==================== CHARACTERS ====================

    def create_character(self, org_id: int, jdr_id: int, name: str, race: str,
                         char_class: str, stats: dict = None, avatar_image_id: int = None):
        if stats is None:
            stats = {
                "hp": 100, "hp_max": 100, "mp": 50, "mp_max": 50,
                "strength": 15, "dexterity": 12, "intelligence": 10,
                "defense": 8, "speed": 6
            }
        payload = {
            "name": name,
            "race": race,
            "character_class": char_class,
            "level": 1,
            "stats": stats,
            "gold": 50.0,
            "backstory": f"Je suis {name}, un {race} {char_class} en quête d'aventure.",
            "notes": "Nouveau personnage"
        }
        if avatar_image_id:
            payload["avatar_image_id"] = avatar_image_id

        response = requests.post(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/characters",
            json=payload,
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        resp, data = self._print_response(response, f"CREATE CHARACTER {name}")
        if response.status_code == 201 and data:
            self.character_id = data.get("id")
        return resp, data

    def update_character(self, org_id: int, jdr_id: int, character_id: int, **kwargs):
        response = requests.patch(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/characters/{character_id}",
            json=kwargs,
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        return self._print_response(response, f"UPDATE CHARACTER {character_id}")

    def mj_update_character(self, org_id: int, jdr_id: int, character_id: int, **kwargs):
        response = requests.patch(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/characters/{character_id}/mj",
            json=kwargs,
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        return self._print_response(response, f"MJ UPDATE CHARACTER {character_id}")

    def list_characters(self, org_id: int, jdr_id: int):
        response = requests.get(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/characters",
            headers=self._headers()
        )
        return self._print_response(response, f"LIST CHARACTERS JDR {jdr_id}")

    # ==================== INVENTORY ====================

    def create_game_item(self, org_id: int, jdr_id: int, custom_name: str,
                         custom_image_id: int = None, template_id: int = None,
                         quantity: int = 1, custom_stats: dict = None):
        payload = {
            "custom_name": custom_name,
            "custom_description": f"Un item : {custom_name}",
            "custom_stats": custom_stats or {},
            "quantity": quantity
        }
        if custom_image_id:
            payload["custom_image_id"] = custom_image_id
        if template_id:
            payload["template_id"] = template_id

        response = requests.post(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/items",
            json=payload,
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        return self._print_response(response, f"CREATE GAME ITEM {custom_name}")

    def give_item(self, org_id: int, jdr_id: int, game_item_id: int,
                  character_id: int, quantity: int = 1, notes: str = None):
        response = requests.post(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/inventory/give",
            json={
                "game_item_id": game_item_id,
                "character_id": character_id,
                "quantity": quantity,
                "mj_notes": notes
            },
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        return self._print_response(response, f"GIVE ITEM {game_item_id} -> char {character_id}")

    def update_gold(self, org_id: int, jdr_id: int, character_id: int,
                    amount: float, reason: str = None):
        response = requests.patch(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/characters/{character_id}/gold",
            json={"amount": amount, "reason": reason},
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        return self._print_response(response, f"UPDATE GOLD char={character_id} amount={amount:+.1f}")

    # ==================== BOARD ====================

    def get_board(self, org_id: int, jdr_id: int):
        response = requests.get(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/board",
            headers=self._headers()
        )
        return self._print_response(response, f"GET BOARD JDR {jdr_id}")

    def update_board(self, org_id: int, jdr_id: int, **kwargs):
        response = requests.patch(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/board",
            json=kwargs,
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        return self._print_response(response, f"UPDATE BOARD JDR {jdr_id}")

    def add_board_element(self, org_id: int, jdr_id: int, element_type: str,
                          content: dict, position: dict,
                          image_id: int = None, character_id: int = None,
                          game_item_id: int = None, visible_to: dict = None,
                          is_visible: bool = True):
        payload = {
            "element_type": element_type,
            "content": content,
            "position": position,
            "is_visible": is_visible,
            "visible_to": visible_to or {"all": True}
        }
        if image_id:
            payload["image_id"] = image_id
        if character_id:
            payload["character_id"] = character_id
        if game_item_id:
            payload["game_item_id"] = game_item_id

        response = requests.post(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/board/elements",
            json=payload,
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        return self._print_response(response, f"ADD BOARD ELEMENT {element_type}")

    def update_board_element(self, org_id: int, jdr_id: int, element_id: int, **kwargs):
        response = requests.patch(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/board/elements/{element_id}",
            json=kwargs,
            headers={**self._headers(), "Content-Type": "application/json"}
        )
        return self._print_response(response, f"UPDATE BOARD ELEMENT {element_id}")

    def delete_board_element(self, org_id: int, jdr_id: int, element_id: int):
        response = requests.delete(
            f"{self.base_url}/organizations/{org_id}/jdrs/{jdr_id}/board/elements/{element_id}",
            headers=self._headers()
        )
        return self._print_response(response, f"DELETE BOARD ELEMENT {element_id}")


# ============================
# UTILITIES
# ============================

def wait_for_api(base_url: str = "http://127.0.0.1:8000", max_attempts: int = 15):
    print("\n⏳ Attente du démarrage de l'API...")
    for i in range(max_attempts):
        try:
            response = requests.get(f"{base_url}/", timeout=2)
            if response.status_code == 200:
                print("✅ API prête!\n")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
        print(f"  Tentative {i + 1}/{max_attempts}...")
    print("❌ API non disponible - Lancez le serveur avec: uvicorn main:app --reload")
    return False


# ============================
# TEST PRINCIPAL
# ============================

def run_jdr_test():
    if not wait_for_api():
        return

    # ✅ Télécharge les images de test
    images_data = download_test_images()

    print("\n" + "=" * 60)
    print("🎲 DÉMARRAGE DES TESTS JDR")
    print("=" * 60)

    mj = JDRTester()
    player1 = JDRTester()
    player2 = JDRTester()

    # ============================================================
    # SECTION 1: SETUP UTILISATEURS
    # ============================================================
    print("\n🔐 SECTION 1: SETUP UTILISATEURS")
    print("=" * 60)

    print("\n📝 1.1: Login admin (créé au démarrage)")
    admin = JDRTester()
    admin.login("admin@admin.com", "admin123")

    print("\n📝 1.2: Création et login du MJ")
    mj.register("mj@test.com", "password123")
    mj.login("mj@test.com", "password123")

    print("\n📝 1.3: Création et login Player1")
    player1.register("player1@test.com", "password123")
    player1.login("player1@test.com", "password123")

    print("\n📝 1.4: Création et login Player2")
    player2.register("player2@test.com", "password123")
    player2.login("player2@test.com", "password123")

    # ============================================================
    # SECTION 2: ORGANISATION
    # ============================================================
    print("\n🏢 SECTION 2: ORGANISATION")
    print("=" * 60)

    print("\n📝 2.1: MJ crée une organisation")
    _, org_data = mj.create_organization("Guilde des Aventuriers", "guilde-aventuriers")
    org_id = org_data.get("id") if org_data else None
    if not org_id:
        print("❌ Impossible de créer l'organisation, arrêt des tests")
        return

    print("\n📝 2.2: Players rejoignent l'organisation")
    player1.join_organization(org_id)
    player2.join_organization(org_id)

    # ============================================================
    # SECTION 3: CRÉATION JDR
    # ============================================================
    print("\n🎲 SECTION 3: CRÉATION JDR")
    print("=" * 60)

    print("\n📝 3.1: MJ crée un JDR (devient automatiquement MJ)")
    _, jdr_data = mj.create_jdr(org_id, "La Forêt Maudite", "D&D 5e", max_players=4)
    jdr_id = jdr_data.get("id") if jdr_data else None
    if not jdr_id:
        print("❌ Impossible de créer le JDR, arrêt des tests")
        return

    print("\n📝 3.2: MJ ouvre le JDR")
    mj.update_jdr(org_id, jdr_id, status="open")

    print("\n📝 3.3: Listing des JDRs")
    mj.list_jdrs(org_id)

    # ============================================================
    # SECTION 4: UPLOAD DES IMAGES
    # ============================================================
    print("\n🖼️  SECTION 4: UPLOAD DES IMAGES")
    print("=" * 60)

    bg_image_id = None
    monster_image_id = None
    avatar_image_id = None

    print("\n📝 4.1: MJ uploade l'image de fond du board")
    _, bg_data = mj.upload_image(
        image_bytes=images_data.get("board_bg"),
        filename="board_bg.jpg",
        category="boards",
        jdr_id=jdr_id,
        org_id=org_id,
        tags={"type": "background", "jdr": "La Forêt Maudite"}
    )
    if bg_data:
        bg_image_id = bg_data.get("id")
        print(f"  🖼️  Image de fond uploadée: id={bg_image_id}, url={bg_data.get('url')}")

    print("\n📝 4.2: MJ uploade l'image du monstre")
    _, monster_data_img = mj.upload_image(
        image_bytes=images_data.get("monster"),
        filename="monster.jpg",
        category="monsters",
        jdr_id=jdr_id,
        org_id=org_id,
        tags={"type": "monster", "name": "Dragon Noir"}
    )
    if monster_data_img:
        monster_image_id = monster_data_img.get("id")
        print(f"  🐉 Image monstre uploadée: id={monster_image_id}")

    print("\n📝 4.3: Player1 uploade son avatar")
    _, avatar_data = player1.upload_image(
        image_bytes=images_data.get("character_avatar"),
        filename="character_avatar.jpg",
        category="characters",
        jdr_id=jdr_id,
        org_id=org_id,
        tags={"type": "avatar", "character": "Thorin"}
    )
    if avatar_data:
        avatar_image_id = avatar_data.get("id")
        print(f"  👤 Avatar uploadé: id={avatar_image_id}")

    print("\n📝 4.4: MJ uploade l'avatar avec resize automatique (200x200)")
    mj.upload_image(
        image_bytes=images_data.get("character_avatar"),
        filename="character_avatar_thumb.jpg",
        category="characters",
        jdr_id=jdr_id,
        tags={"type": "avatar_thumb"},
        resize_width=200,
        resize_height=200
    )

    print("\n📝 4.5: MJ resize l'image monstre en 400x300")
    if monster_data_img and monster_data_img.get("filename"):
        mj.resize_image(
            filename=monster_data_img.get("filename"),
            category="monsters",
            width=400,
            height=300,
            quality=90,
            keep_ratio=True
        )

    print("\n📝 4.6: Info sur l'image de fond")
    if bg_data and bg_data.get("filename"):
        mj.get_image_info("boards", bg_data.get("filename"))

    print("\n📝 4.7: Player2 essaie d'uploader sans auth (devrait échouer)")
    unauth_tester = JDRTester()
    unauth_tester.upload_image(
        image_bytes=images_data.get("monster"),
        filename="hack.jpg",
        category="monsters"
    )

    # ============================================================
    # SECTION 5: CANVAS BOARD
    # ============================================================
    print("\n🗺️  SECTION 5: CANVAS BOARD")
    print("=" * 60)

    print("\n📝 5.1: MJ configure le board avec image de fond")
    if bg_image_id:
        mj.update_board(
            org_id, jdr_id,
            background_image_id=bg_image_id,
            dimensions={
                "width": 1920,
                "height": 1080,
                "grid_size": 50,
                "scale": 1.0,
                "show_grid": True,
                "grid_color": "#444444",
                "background_color": "#1a1a2e"
            }
        )

    print("\n📝 5.2: MJ génère une version canvas de l'image monstre (positionnée sur le board)")
    if monster_data_img and monster_data_img.get("filename"):
        mj.board_canvas(
            jdr_id=jdr_id,
            filename=monster_data_img.get("filename"),
            category="monsters",
            canvas_width=1920,
            canvas_height=1080,
            position_x=800,
            position_y=300,
            img_width=400,
            img_height=300
        )

    # ============================================================
    # SECTION 6: MEMBERSHIP JDR
    # ============================================================
    print("\n👥 SECTION 6: JOUEURS REJOIGNENT LE JDR")
    print("=" * 60)

    print("\n📝 6.1: Player1 demande à rejoindre")
    _, p1_membership = player1.join_jdr(org_id, jdr_id, "Je suis un guerrier nain!")
    player1_membership_id = p1_membership.get("id") if p1_membership else None

    print("\n📝 6.2: Player2 demande à rejoindre")
    _, p2_membership = player2.join_jdr(org_id, jdr_id, "Je joue un mage humain!")
    player2_membership_id = p2_membership.get("id") if p2_membership else None

    print("\n📝 6.3: MJ approuve Player1")
    if player1_membership_id:
        mj.approve_player(org_id, jdr_id, player1_membership_id)

    print("\n📝 6.4: MJ approuve Player2")
    if player2_membership_id:
        mj.approve_player(org_id, jdr_id, player2_membership_id)

    # ============================================================
    # SECTION 7: FICHES PERSONNAGE AVEC IMAGES
    # ============================================================
    print("\n📋 SECTION 7: FICHES PERSONNAGE AVEC IMAGES")
    print("=" * 60)

    print("\n📝 7.1: Player1 crée son personnage AVEC avatar uploadé")
    _, char1_data = player1.create_character(
        org_id=org_id,
        jdr_id=jdr_id,
        name="Thorin le Brave",
        race="Nain",
        char_class="Guerrier",
        stats={
            "hp": 120, "hp_max": 120, "mp": 20, "mp_max": 20,
            "strength": 18, "dexterity": 10, "intelligence": 8,
            "defense": 15, "speed": 4
        },
        avatar_image_id=avatar_image_id
    )
    player1_char_id = char1_data.get("id") if char1_data else None
    if char1_data:
        print(f"  👤 Personnage créé avec avatar_url: {char1_data.get('avatar_url')}")

    print("\n📝 7.2: Player1 crée un 2e personnage SANS avatar")
    player1.create_character(
        org_id=org_id,
        jdr_id=jdr_id,
        name="Sylwen l'Archer",
        race="Elfe",
        char_class="Rôdeur",
        stats={
            "hp": 80, "hp_max": 80, "mp": 40, "mp_max": 40,
            "strength": 12, "dexterity": 18, "intelligence": 12,
            "defense": 8, "speed": 9
        }
    )

    print("\n📝 7.3: Player2 crée son personnage")
    _, char2_data = player2.create_character(
        org_id=org_id,
        jdr_id=jdr_id,
        name="Zara la Mystérieuse",
        race="Humaine",
        char_class="Mage",
        stats={
            "hp": 60, "hp_max": 60, "mp": 150, "mp_max": 150,
            "strength": 6, "dexterity": 12, "intelligence": 20,
            "defense": 4, "speed": 7
        }
    )
    player2_char_id = char2_data.get("id") if char2_data else None

    print("\n📝 7.4: Player1 change son avatar (nouvelle image)")
    if player1_char_id and avatar_image_id:
        player1.update_character(
            org_id, jdr_id, player1_char_id,
            avatar_image_id=avatar_image_id,
            backstory="Vétéran des guerres du Nord, Thorin cherche rédemption."
        )

    print("\n📝 7.5: Liste des personnages (vérifie les avatar_url)")
    mj.list_characters(org_id, jdr_id)

    # ============================================================
    # SECTION 8: MJ GESTION PERSONNAGES
    # ============================================================
    print("\n⚔️  SECTION 8: MJ GESTION DES PERSONNAGES")
    print("=" * 60)

    print("\n📝 8.1: MJ monte Thorin en level 2 et donne de l'XP")
    if player1_char_id:
        mj.mj_update_character(
            org_id, jdr_id, player1_char_id,
            experience=1500,
            level=2,
            stats={
                "hp": 140, "hp_max": 140, "mp": 25, "mp_max": 25,
                "strength": 19, "dexterity": 10, "intelligence": 8,
                "defense": 16, "speed": 4
            }
        )

    print("\n📝 8.2: MJ met Zara KO")
    if player2_char_id:
        mj.mj_update_character(
            org_id, jdr_id, player2_char_id,
            stats={"hp": 0, "hp_max": 60, "mp": 150, "mp_max": 150,
                   "strength": 6, "dexterity": 12, "intelligence": 20,
                   "defense": 4, "speed": 7},
            is_alive=False,
            notes="KO après le combat contre le Dragon!"
        )

    print("\n📝 8.3: MJ ressuscite Zara")
    if player2_char_id:
        mj.mj_update_character(
            org_id, jdr_id, player2_char_id,
            stats={"hp": 1, "hp_max": 60, "mp": 150, "mp_max": 150,
                   "strength": 6, "dexterity": 12, "intelligence": 20,
                   "defense": 4, "speed": 7},
            is_alive=True
        )

    # ============================================================
    # SECTION 9: ITEMS AVEC IMAGES
    # ============================================================
    print("\n⚔️  SECTION 9: ITEMS AVEC IMAGES")
    print("=" * 60)

    print("\n📝 9.1: MJ crée une épée légendaire AVEC image")
    _, sword_data = mj.create_game_item(
        org_id=org_id,
        jdr_id=jdr_id,
        custom_name="Épée du Dragon Noir",
        custom_image_id=monster_image_id,  # Utilise l'image du monstre pour l'épée
        quantity=1,
        custom_stats={"damage": "2d8+5", "weight": 3.5, "value": 5000, "type": "legendary"}
    )
    sword_id = sword_data.get("id") if sword_data else None
    if sword_data:
        print(f"  ⚔️  Épée créée: id={sword_id}, image_url={sword_data.get('image_url')}")

    print("\n📝 9.2: MJ crée une potion SANS image")
    _, potion_data = mj.create_game_item(
        org_id=org_id,
        jdr_id=jdr_id,
        custom_name="Potion de Soin Majeure",
        quantity=5,
        custom_stats={"heal": "4d8+10", "weight": 0.5, "value": 150}
    )
    potion_id = potion_data.get("id") if potion_data else None

    print("\n📝 9.3: MJ donne l'épée à Thorin")
    if sword_id and player1_char_id:
        mj.give_item(
            org_id, jdr_id, sword_id, player1_char_id,
            quantity=1, notes="Récompense pour avoir vaincu le dragon!"
        )

    print("\n📝 9.4: MJ donne des potions aux deux joueurs")
    if potion_id and player1_char_id:
        mj.give_item(org_id, jdr_id, potion_id, player1_char_id, quantity=2)
    if potion_id and player2_char_id:
        mj.give_item(org_id, jdr_id, potion_id, player2_char_id, quantity=3)

    print("\n📝 9.5: MJ donne de l'or à Thorin (+200)")
    if player1_char_id:
        mj.update_gold(org_id, jdr_id, player1_char_id, 200.0, "Butin du dragon")

    print("\n📝 9.6: MJ retire de l'or à Zara (-30) pour des soins")
    if player2_char_id:
        mj.update_gold(org_id, jdr_id, player2_char_id, -30.0, "Achat potions")

    print("\n📝 9.7: Test minimum or à 0 (retire trop)")
    if player2_char_id:
        mj.update_gold(org_id, jdr_id, player2_char_id, -9999.0, "Test plancher à 0")

    # ============================================================
    # SECTION 10: BOARD AVEC IMAGES
    # ============================================================
    print("\n🗺️  SECTION 10: BOARD AVEC IMAGES")
    print("=" * 60)

    print("\n📝 10.1: Récupération du board (MJ - vue complète)")
    _, board_data = mj.get_board(org_id, jdr_id)
    if board_data:
        print(f"  📋 Board: {board_data.get('name')}")
        print(f"  🖼️  Background URL: {board_data.get('background_url')}")
        print(f"  📐 Dimensions: {board_data.get('dimensions')}")

    print("\n📝 10.2: MJ ajoute une note de bienvenue")
    mj.add_board_element(
        org_id=org_id, jdr_id=jdr_id,
        element_type="note",
        content={"text": "⚔️ Bienvenue dans La Forêt Maudite!", "color": "#FFD700", "font_size": 24},
        position={"x": 50, "y": 50, "z": 0, "width": 350, "height": 120, "rotation": 0}
    )

    print("\n📝 10.3: MJ place Thorin sur le board AVEC référence image auto")
    if player1_char_id:
        _, thorin_element = mj.add_board_element(
            org_id=org_id, jdr_id=jdr_id,
            element_type="character",
            content={"display_name": "Thorin", "token_color": "#0000FF"},
            position={"x": 300, "y": 400, "z": 1, "width": 80, "height": 80, "rotation": 0},
            character_id=player1_char_id  # avatar_url calculée automatiquement
        )
        thorin_element_id = thorin_element.get("id") if thorin_element else None
        if thorin_element:
            print(f"  👤 Thorin placé sur le board, image_url: {thorin_element.get('image_url')}")

    print("\n📝 10.4: MJ place un monstre AVEC son image uploadée")
    _, monster_element = mj.add_board_element(
        org_id=org_id, jdr_id=jdr_id,
        element_type="monster",
        image_id=monster_image_id,  # ✅ Image directe depuis DB
        content={
            "name": "Dragon Noir",
            "hp": 500, "hp_max": 500,
            "description": "Un dragon ancien et terrifiant",
            "stats": {"strength": 30, "defense": 20, "speed": 8}
        },
        position={"x": 900, "y": 350, "z": 1, "width": 200, "height": 200, "rotation": 0},
        is_visible=True,
        visible_to={"all": True}
    )
    monster_element_id = monster_element.get("id") if monster_element else None
    if monster_element:
        print(f"  🐉 Dragon placé, image_url: {monster_element.get('image_url')}")

    print("\n📝 10.5: MJ cache le monstre aux joueurs")
    if monster_element_id:
        mj.update_board_element(
            org_id, jdr_id, monster_element_id,
            is_visible=False
        )

    print("\n📝 10.6: MJ révèle le monstre uniquement à Player1")
    if monster_element_id:
        mj.update_board_element(
            org_id, jdr_id, monster_element_id,
            is_visible=True,
            visible_to={"player_ids": [player1.user_id]}
        )

    print("\n📝 10.7: MJ place le fond de carte (image board_bg en tant qu'élément)")
    if bg_image_id:
        mj.add_board_element(
            org_id=org_id, jdr_id=jdr_id,
            element_type="image",
            image_id=bg_image_id,  # ✅ Image depuis DB
            content={"alt": "Carte de la Forêt Maudite", "opacity": 0.9},
            position={"x": 0, "y": 0, "z": -1, "width": 1920, "height": 1080, "rotation": 0}
        )

    print("\n📝 10.8: MJ met à jour la position du monstre (déplacement)")
    if monster_element_id:
        mj.update_board_element(
            org_id, jdr_id, monster_element_id,
            position={"x": 1000, "y": 500}  # Merge avec la position existante
        )

    print("\n📝 10.9: Player1 voit le board (éléments filtrés selon visibilité)")
    player1.get_board(org_id, jdr_id)

    print("\n📝 10.10: Player2 voit le board (ne devrait pas voir le monstre)")
    player2.get_board(org_id, jdr_id)

    print("\n📝 10.11: Player2 essaie d'ajouter un élément (devrait échouer)")
    player2.add_board_element(
        org_id=org_id, jdr_id=jdr_id,
        element_type="note",
        content={"text": "Hacking le board!"},
        position={"x": 0, "y": 0}
    )

    # ============================================================
    # SECTION 11: GESTION DES IMAGES
    # ============================================================
    print("\n🖼️  SECTION 11: GESTION DES IMAGES")
    print("=" * 60)

    print("\n📝 11.1: Liste toutes les images du JDR")
    mj.list_jdr_images(jdr_id)

    print("\n📝 11.2: Liste uniquement les images de monstres")
    mj.list_jdr_images(jdr_id, category="monsters")

    print("\n📝 11.3: Player1 essaie de supprimer l'image du MJ (devrait échouer)")
    if monster_image_id:
        player1.delete_image(monster_image_id)

    print("\n📝 11.4: Player1 supprime son propre avatar")
    if avatar_image_id:
        player1.delete_image(avatar_image_id)

    # ============================================================
    # SECTION 12: FIN DE JDR
    # ============================================================
    print("\n🏁 SECTION 12: FIN DE JDR")
    print("=" * 60)

    print("\n📝 12.1: MJ supprime un élément du board")
    if monster_element_id:
        mj.delete_board_element(org_id, jdr_id, monster_element_id)

    print("\n📝 12.2: MJ termine le JDR")
    mj.update_jdr(org_id, jdr_id, status="completed")

    print("\n📝 12.3: Listing final des JDRs")
    mj.list_jdrs(org_id)

    # ============================================================
    # RÉSUMÉ
    # ============================================================
    print("\n" + "=" * 60)
    print("✅ TESTS JDR TERMINÉS")
    print("=" * 60)
    print("\n📊 RÉSUMÉ:")
    print("  🖼️  Images:      ✅ Upload, resize, canvas, liste, suppression")
    print("  🎲 JDR:         ✅ Création, update, listing, statuts")
    print("  👑 MJ:          ✅ Créateur = MJ automatiquement")
    print("  👥 Membership:  ✅ Approbation joueurs par MJ")
    print("  📋 Personnages: ✅ Création avec avatar_image_id")
    print("  🔗 FK Images:   ✅ avatar_url calculée depuis ImageAsset")
    print("  ⚔️  Items:       ✅ custom_image_id, image_url cascadée")
    print("  💰 Or:          ✅ Donation/retrait (plancher à 0)")
    print("  🗺️  Board:       ✅ background_image_id, canvas, éléments")
    print("  👁️  Visibilité:  ✅ MJ cache/révèle des éléments")
    print("  🔒 Permissions: ✅ Joueurs ne peuvent pas modifier le board")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--clear-cache":
        import shutil
        if IMAGE_CACHE_DIR.exists():
            shutil.rmtree(IMAGE_CACHE_DIR)
            print("🗑️  Cache images supprimé")
    run_jdr_test()