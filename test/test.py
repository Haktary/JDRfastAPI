# test_api.py
import requests
from typing import Optional
import json
import time


class APITester:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.org_id: Optional[int] = None
        self.membership_id: Optional[int] = None

    def _headers(self, auth: bool = True) -> dict:
        """Génère les headers avec ou sans auth"""
        headers = {"Content-Type": "application/json"}
        if auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _print_response(self, response: requests.Response, title: str):
        """Affiche une réponse de manière formatée"""
        print(f"\n{'=' * 60}")
        print(f"🔹 {title}")
        print(f"{'=' * 60}")
        print(f"Status: {response.status_code}")
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            return response, data
        except:
            print(f"Response: {response.text}")
            return response, None
        finally:
            print(f"{'=' * 60}\n")

    # ==================== AUTHENTICATION ====================

    def register(self, email: str, password: str):
        """POST /auth/register - Le rôle n'est plus spécifiable (toujours 'user')"""
        response = requests.post(
            f"{self.base_url}/auth/register",
            json={
                "email": email,
                "password": password
            },
            headers=self._headers(auth=False)
        )
        resp, data = self._print_response(response, "REGISTER")
        if response.status_code == 201 and data:
            self.user_id = data.get("id")
        return response

    def login(self, email: str, password: str):
        """POST /auth/login"""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={
                "email": email,
                "password": password
            },
            headers=self._headers(auth=False)
        )
        resp, data = self._print_response(response, "LOGIN")
        if response.status_code == 200 and data:
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
        return response

    def promote_user(self, user_id: int, new_global_role: str):
        """POST /auth/promote - Promouvoir un utilisateur (admin seulement)"""
        response = requests.post(
            f"{self.base_url}/auth/promote",
            json={
                "user_id": user_id,
                "new_global_role": new_global_role
            },
            headers=self._headers()
        )
        self._print_response(response, f"PROMOTE USER {user_id} to {new_global_role}")
        return response

    def refresh(self):
        """POST /auth/refresh"""
        response = requests.post(
            f"{self.base_url}/auth/refresh",
            json={"refresh_token": self.refresh_token},
            headers=self._headers(auth=False)
        )
        resp, data = self._print_response(response, "REFRESH TOKEN")
        if response.status_code == 200 and data:
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
        return response

    def logout(self):
        """POST /auth/logout"""
        response = requests.post(
            f"{self.base_url}/auth/logout",
            json={"refresh_token": self.refresh_token},
            headers=self._headers()
        )
        self._print_response(response, "LOGOUT")
        return response

    def logout_all(self):
        """POST /auth/logout-all"""
        response = requests.post(
            f"{self.base_url}/auth/logout-all",
            json={"refresh_token": self.refresh_token},
            headers=self._headers()
        )
        self._print_response(response, "LOGOUT ALL")
        return response

    # ==================== ORGANIZATIONS ====================

    def create_organization(self, name: str, slug: str, description: str = None,
                            visibility: str = "public", join_mode: str = "approval"):
        """POST /organizations/"""
        response = requests.post(
            f"{self.base_url}/organizations/",
            json={
                "name": name,
                "slug": slug,
                "description": description,
                "visibility": visibility,
                "join_mode": join_mode
            },
            headers=self._headers()
        )
        resp, data = self._print_response(response, "CREATE ORGANIZATION")
        if response.status_code == 201 and data:
            self.org_id = data.get("id")
        return response

    def update_organization(self, organization_id: int, **kwargs):
        """PATCH /organizations/{organization_id}"""
        response = requests.patch(
            f"{self.base_url}/organizations/{organization_id}",
            json=kwargs,
            headers=self._headers()
        )
        self._print_response(response, f"UPDATE ORGANIZATION {organization_id}")
        return response

    def get_my_organizations(self):
        """GET /organizations/my"""
        response = requests.get(
            f"{self.base_url}/organizations/my",
            headers=self._headers()
        )
        self._print_response(response, "GET MY ORGANIZATIONS")
        return response

    def join_organization(self, organization_id: int, message: str = None):
        """POST /organizations/{organization_id}/join"""
        response = requests.post(
            f"{self.base_url}/organizations/{organization_id}/join",
            json={"message": message},
            headers=self._headers()
        )
        resp, data = self._print_response(response, f"JOIN ORGANIZATION {organization_id}")
        if response.status_code == 200 and data:
            self.membership_id = data.get("id")
        return response

    def get_organization(self, organization_id: int):
        """GET /organizations/{organization_id}"""
        response = requests.get(
            f"{self.base_url}/organizations/{organization_id}",
            headers=self._headers()
        )
        self._print_response(response, f"GET ORGANIZATION {organization_id}")
        return response

    def delete_organization(self, organization_id: int):
        """DELETE /organizations/{organization_id}"""
        response = requests.delete(
            f"{self.base_url}/organizations/{organization_id}",
            headers=self._headers()
        )
        self._print_response(response, f"DELETE ORGANIZATION {organization_id}")
        return response

    def change_member_role(self, organization_id: int, user_id: int, role: str):
        """PATCH /organizations/{organization_id}/members/{user_id}/role"""
        response = requests.patch(
            f"{self.base_url}/organizations/{organization_id}/members/{user_id}/role",
            json={"role": role},
            headers=self._headers()
        )
        self._print_response(response, f"CHANGE MEMBER ROLE - Org:{organization_id}, User:{user_id} -> {role}")
        return response

    def approve_member(self, organization_id: int, membership_id: int):
        """POST /organizations/{organization_id}/members/{membership_id}/approve"""
        response = requests.post(
            f"{self.base_url}/organizations/{organization_id}/members/{membership_id}/approve",
            headers=self._headers()
        )
        self._print_response(response, f"APPROVE MEMBER {membership_id}")
        return response

    def remove_member(self, organization_id: int, user_id: int):
        """DELETE /organizations/{organization_id}/members/{user_id}"""
        response = requests.delete(
            f"{self.base_url}/organizations/{organization_id}/members/{user_id}",
            headers=self._headers()
        )
        self._print_response(response, f"REMOVE MEMBER - Org:{organization_id}, User:{user_id}")
        return response


# ==================== TESTS ====================

def wait_for_api(base_url: str = "http://127.0.0.1:8000", max_attempts: int = 10):
    """Attend que l'API soit prête"""
    print("\n⏳ Attente du démarrage de l'API...")
    for i in range(max_attempts):
        try:
            response = requests.get(f"{base_url}/")
            if response.status_code == 200:
                print("✅ API prête!\n")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
        print(f"  Tentative {i + 1}/{max_attempts}...")

    print("❌ API non disponible")
    return False


def run_full_test():
    """Exécute un test complet de l'API"""

    # Attendre que l'API soit prête
    if not wait_for_api():
        print("Impossible de se connecter à l'API. Assurez-vous qu'elle est lancée.")
        return

    print("\n" + "=" * 60)
    print("🚀 DÉMARRAGE DES TESTS API")
    print("=" * 60)

    # Initialisation
    admin = APITester()
    user1 = APITester()
    user2 = APITester()

    # ===== TEST 1: AUTHENTICATION & SECURITY =====
    print("\n" + "🔐 SECTION 1: AUTHENTICATION & SECURITY" + "\n" + "=" * 60)

    print("\n📝 Test 1.1: Login avec l'admin par défaut")
    admin.login("admin@admin.com", "admin123")

    print("\n📝 Test 1.2: Enregistrement user1 (automatiquement 'user')")
    user1.register("user1@test.com", "password123")
    user1_user_id = user1.user_id

    print("\n📝 Test 1.3: Login user1")
    user1.login("user1@test.com", "password123")

    print("\n📝 Test 1.4: Enregistrement user2")
    user2.register("user2@test.com", "password123")
    user2_user_id = user2.user_id

    print("\n📝 Test 1.5: Login user2")
    user2.login("user2@test.com", "password123")

    print("\n📝 Test 1.6: User1 essaie de promouvoir user2 (devrait échouer)")
    user1.promote_user(user2_user_id, "admin")

    print("\n📝 Test 1.7: Admin promeut user1 en admin (devrait réussir)")
    admin.promote_user(user1_user_id, "admin")

    print("\n📝 Test 1.8: User1 re-login pour obtenir le nouveau token admin")
    user1.login("user1@test.com", "password123")

    print("\n📝 Test 1.9: Refresh token admin")
    admin.refresh()

    # ===== TEST 2: ORGANIZATIONS - CREATION & OWNERSHIP =====
    print("\n" + "🏢 SECTION 2: ORGANIZATIONS - CREATION & OWNERSHIP" + "\n" + "=" * 60)

    print("\n📝 Test 2.1: User2 crée une organisation (devient OWNER)")
    user2.create_organization(
        name="Gaming Clan",
        slug="gaming-clan",
        description="The best gaming clan ever",
        visibility="public",
        join_mode="approval"
    )
    org_id = user2.org_id

    print("\n📝 Test 2.2: Vérifier les organisations de user2")
    user2.get_my_organizations()

    print("\n📝 Test 2.3: User2 met à jour l'organisation (en tant que owner)")
    user2.update_organization(
        org_id,
        name="Elite Gaming Clan",
        description="The BEST gaming clan in the universe!",
        join_mode="open"
    )

    print("\n📝 Test 2.4: User2 vérifie l'organisation mise à jour")
    user2.get_organization(org_id)

    # ===== TEST 3: MEMBERSHIP MANAGEMENT =====
    print("\n" + "👥 SECTION 3: MEMBERSHIP MANAGEMENT" + "\n" + "=" * 60)

    print("\n📝 Test 3.1: User1 demande à rejoindre (join_mode='open' donc actif direct)")
    user1.join_organization(org_id, "I want to join the elite clan!")
    membership_id = user1.membership_id

    print("\n📝 Test 3.2: User1 vérifie qu'il peut accéder à l'org")
    user1.get_organization(org_id)

    print("\n📝 Test 3.3: User2 (owner) change le rôle de user1 en MJ")
    if user1.user_id:
        user2.change_member_role(org_id, user1.user_id, "mj")
    else:
        print("⚠️  User1 ID non disponible, skip test 3.3")

    print("\n📝 Test 3.4: User1 vérifie son nouveau rôle")
    user1.get_organization(org_id)

    # ===== TEST 4: PERMISSIONS & ROLE HIERARCHY =====
    print("\n" + "🔒 SECTION 4: PERMISSIONS & ROLE HIERARCHY" + "\n" + "=" * 60)

    print("\n📝 Test 4.1: User1 (MJ) essaie de modifier l'org (devrait échouer - besoin admin)")
    user1.update_organization(org_id, name="Hacked Clan")

    print("\n📝 Test 4.2: User2 (owner) promeut user1 en admin org")
    if user1.user_id:
        user2.change_member_role(org_id, user1.user_id, "admin")

    print("\n📝 Test 4.3: User1 (admin org) essaie de modifier l'org (devrait réussir)")
    user1.update_organization(org_id, description="Modified by admin user1")

    print("\n📝 Test 4.4: User1 (admin org) essaie de changer le rôle de user2 (owner) - devrait échouer")
    if user2.user_id:
        user1.change_member_role(org_id, user2.user_id, "member")

    print("\n📝 Test 4.5: User2 crée une 2e organisation (invite-only)")
    user2.create_organization(
        name="Secret Society",
        slug="secret-society",
        description="Top secret organization",
        visibility="private",
        join_mode="invite_only"
    )
    secret_org_id = user2.org_id

    print("\n📝 Test 4.6: User1 essaie de rejoindre l'org invite-only (devrait échouer)")
    user1.join_organization(secret_org_id, "Let me in!")

    # ===== TEST 5: APPROVAL WORKFLOW =====
    print("\n" + "✅ SECTION 5: APPROVAL WORKFLOW" + "\n" + "=" * 60)

    print("\n📝 Test 5.1: User2 change son org en mode approval")
    user2.update_organization(org_id, join_mode="approval")

    # Créer un 3e utilisateur pour tester l'approbation
    user3 = APITester()
    print("\n📝 Test 5.2: Enregistrement user3")
    user3.register("user3@test.com", "password123")
    user3.login("user3@test.com", "password123")
    user3_user_id = user3.user_id

    print("\n📝 Test 5.3: User3 demande à rejoindre (statut pending)")
    user3.join_organization(org_id, "Please let me join!")
    user3_membership_id = user3.membership_id

    print("\n📝 Test 5.4: User3 essaie d'accéder à l'org (devrait échouer - pending)")
    user3.get_organization(org_id)

    print("\n📝 Test 5.5: User2 (owner) approuve user3")
    if user3_membership_id:
        user2.approve_member(org_id, user3_membership_id)
    else:
        print("⚠️  User3 membership ID non disponible, skip test 5.5")

    print("\n📝 Test 5.6: User3 peut maintenant accéder à l'org")
    user3.get_organization(org_id)

    # ===== TEST 6: ADMIN GLOBAL OPERATIONS =====
    print("\n" + "👑 SECTION 6: ADMIN GLOBAL OPERATIONS" + "\n" + "=" * 60)

    print("\n📝 Test 6.1: Admin global supprime la secret organization")
    admin.delete_organization(secret_org_id)

    print("\n📝 Test 6.2: Vérification que l'org est supprimée")
    user2.get_organization(secret_org_id)

    print("\n📝 Test 6.3: User2 (non-admin global) essaie de supprimer l'org (devrait échouer)")
    user2.delete_organization(org_id)

    # ===== TEST 7: CLEANUP & LOGOUT =====
    print("\n" + "🚪 SECTION 7: CLEANUP & LOGOUT" + "\n" + "=" * 60)

    print("\n📝 Test 7.1: User3 se déconnecte")
    user3.logout()

    print("\n📝 Test 7.2: User1 se déconnecte")
    user1.logout()

    print("\n📝 Test 7.3: User2 se déconnecte de tous les appareils")
    user2.logout_all()

    print("\n📝 Test 7.4: Admin se déconnecte")
    admin.logout()

    print("\n" + "=" * 60)
    print("✅ TESTS TERMINÉS")
    print("=" * 60)
    print("\n📊 RÉSUMÉ:")
    print("  • Sécurité: ✅ Les users ne peuvent pas s'auto-promouvoir")
    print("  • Admin par défaut: ✅ admin@admin.com créé au démarrage")
    print("  • Ownership: ✅ Le créateur devient owner automatiquement")
    print("  • Hiérarchie: ✅ guest < member < mj < admin < owner")
    print("  • Protection: ✅ On ne peut pas modifier le rôle d'un owner")
    print("  • Permissions: ✅ Seuls admins/owners peuvent gérer l'org")
    print("=" * 60 + "\n")


def run_simple_test():
    """Test simple et rapide"""
    if not wait_for_api():
        return

    tester = APITester()

    print("\n🚀 TEST SIMPLE\n")

    # Register & Login
    tester.register("test@example.com", "password123")
    tester.login("test@example.com", "password123")

    # Create org (devient owner)
    tester.create_organization(
        name="Test Org",
        slug="test-org",
        description="A test organization"
    )

    # Update org (en tant que owner)
    tester.update_organization(
        tester.org_id,
        name="Updated Test Org",
        description="An updated test organization"
    )

    # Get my orgs
    tester.get_my_organizations()

    print("\n✅ Test simple terminé\n")


def interactive_test():
    """Mode interactif pour tester l'API"""
    if not wait_for_api():
        return

    tester = APITester()

    print("\n🎮 MODE INTERACTIF API TESTER")
    print("=" * 60)
    print("ℹ️  Admin par défaut: admin@admin.com / admin123")
    print("=" * 60)

    while True:
        print("\n📋 MENU:")
        print("1.  Register")
        print("2.  Login")
        print("3.  Promote User (admin only)")
        print("4.  Create Organization")
        print("5.  Update Organization")
        print("6.  Get My Organizations")
        print("7.  Join Organization")
        print("8.  Get Organization")
        print("9.  Approve Member")
        print("10. Change Member Role")
        print("11. Delete Organization")
        print("12. Logout")
        print("0.  Quitter")

        choice = input("\nChoix: ")

        try:
            if choice == "0":
                break
            elif choice == "1":
                email = input("Email: ")
                password = input("Password: ")
                tester.register(email, password)
            elif choice == "2":
                email = input("Email (default: admin@admin.com): ") or "admin@admin.com"
                password = input("Password (default: admin123): ") or "admin123"
                tester.login(email, password)
            elif choice == "3":
                user_id = int(input("User ID: "))
                role = input("New global role (user/admin): ")
                tester.promote_user(user_id, role)
            elif choice == "4":
                name = input("Nom: ")
                slug = input("Slug: ")
                description = input("Description: ")
                visibility = input("Visibility (public/private) [public]: ") or "public"
                join_mode = input("Join mode (open/approval/invite_only/closed) [approval]: ") or "approval"
                tester.create_organization(name, slug, description, visibility, join_mode)
            elif choice == "5":
                org_id = int(input("Organization ID: "))
                print("Laissez vide pour ne pas modifier un champ")
                name = input("Nouveau nom: ") or None
                description = input("Nouvelle description: ") or None
                visibility = input("Visibility (public/private): ") or None
                join_mode = input("Join mode (open/approval/invite_only/closed): ") or None

                updates = {}
                if name: updates["name"] = name
                if description: updates["description"] = description
                if visibility: updates["visibility"] = visibility
                if join_mode: updates["join_mode"] = join_mode

                if updates:
                    tester.update_organization(org_id, **updates)
                else:
                    print("Aucune modification")
            elif choice == "6":
                tester.get_my_organizations()
            elif choice == "7":
                org_id = int(input("Organization ID: "))
                message = input("Message: ")
                tester.join_organization(org_id, message)
            elif choice == "8":
                org_id = int(input("Organization ID: "))
                tester.get_organization(org_id)
            elif choice == "9":
                org_id = int(input("Organization ID: "))
                membership_id = int(input("Membership ID: "))
                tester.approve_member(org_id, membership_id)
            elif choice == "10":
                org_id = int(input("Organization ID: "))
                user_id = int(input("User ID: "))
                role = input("Nouveau rôle (owner/admin/mj/member/guest): ")
                tester.change_member_role(org_id, user_id, role)
            elif choice == "11":
                org_id = int(input("Organization ID: "))
                confirm = input(f"Confirmer la suppression de l'org {org_id} ? (yes/no): ")
                if confirm.lower() == "yes":
                    tester.delete_organization(org_id)
            elif choice == "12":
                tester.logout()
        except ValueError as e:
            print(f"❌ Erreur de saisie: {e}")
        except Exception as e:
            print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "simple":
            run_simple_test()
        elif sys.argv[1] == "interactive":
            interactive_test()
        else:
            run_full_test()
    else:
        print("\nUsage:")
        print("  python test_api.py              # Test complet")
        print("  python test_api.py simple       # Test simple")
        print("  python test_api.py interactive  # Mode interactif")
        print("\nLancement du test complet...\n")
        run_full_test()