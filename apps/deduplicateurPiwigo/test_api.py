#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour tester l'API Piwigo et exporter les données d'un album
Utile pour déboguer pourquoi aucun doublon n'est détecté
"""

import requests
import json
import sys

def test_piwigo_api(piwigo_url, username, password, album_id=None):
    """Teste la connexion et récupère les données d'un album"""
    
    session = requests.Session()
    
    # 1. Test de connexion
    print(f"\n{'='*60}")
    print("1. TEST DE CONNEXION")
    print(f"{'='*60}\n")
    
    try:
        url = f"{piwigo_url}/ws.php?format=json"
        response = session.post(url, data={
            'method': 'pwg.session.login',
            'username': username,
            'password': password
        })
        result = response.json()
        
        if result.get('stat') == 'ok':
            print("✓ Connexion réussie!")
        else:
            print(f"✗ Échec de connexion: {result}")
            return
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return
    
    # 2. Liste des albums
    print(f"\n{'='*60}")
    print("2. LISTE DES ALBUMS")
    print(f"{'='*60}\n")
    
    try:
        response = session.post(url, data={
            'method': 'pwg.categories.getList',
            'recursive': 'true'
        })
        result = response.json()
        
        if result.get('stat') == 'ok':
            albums = result.get('result', {}).get('categories', [])
            print(f"✓ {len(albums)} albums trouvés:\n")
            
            for album in albums[:10]:  # Afficher les 10 premiers
                print(f"  ID {album['id']}: {album['name']} ({album.get('nb_images', 0)} images)")
            
            if len(albums) > 10:
                print(f"\n  ... et {len(albums) - 10} autres albums")
            
            # Si aucun album_id n'est spécifié, demander
            if album_id is None:
                print("\n" + "="*60)
                album_id = input("Entrez l'ID de l'album à analyser (ou ENTER pour le premier): ").strip()
                if not album_id:
                    album_id = albums[0]['id'] if albums else None
                else:
                    album_id = int(album_id)
        else:
            print(f"✗ Erreur: {result}")
            return
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return
    
    if album_id is None:
        print("\n✗ Aucun album disponible")
        return
    
    # 3. Récupération des images de l'album
    print(f"\n{'='*60}")
    print(f"3. IMAGES DE L'ALBUM {album_id}")
    print(f"{'='*60}\n")
    
    try:
        response = session.post(url, data={
            'method': 'pwg.categories.getImages',
            'cat_id': album_id,
            'per_page': 1000
        })
        result = response.json()
        
        if result.get('stat') == 'ok':
            images = result.get('result', {}).get('images', [])
            print(f"✓ {len(images)} images trouvées\n")
            
            # Afficher les détails des premières images
            for i, img in enumerate(images[:5]):
                print(f"\nImage {i+1} (ID: {img['id']}):")
                print(f"  Nom: {img.get('name', 'N/A')}")
                print(f"  Description (comment): {img.get('comment', 'N/A')[:200]}...")
                print(f"  Taille: {img.get('width', '?')}x{img.get('height', '?')}")
                print(f"  Date: {img.get('date_creation', 'N/A')}")
            
            if len(images) > 5:
                print(f"\n  ... et {len(images) - 5} autres images")
            
            # Exporter vers un fichier JSON
            output_file = f"album_{album_id}_images.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(images, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Données exportées vers: {output_file}")
            print(f"\nVous pouvez maintenant utiliser ce fichier avec debug_duplicates.py:")
            print(f"  python debug_duplicates.py")
            print(f"  Puis entrer: {output_file}")
            
        else:
            print(f"✗ Erreur: {result}")
            return
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return
    
    print(f"\n{'='*60}")
    print("✓ Test terminé avec succès!")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("OUTIL DE TEST API PIWIGO")
    print("="*60 + "\n")
    
    # Demander les informations
    piwigo_url = input("URL de votre site Piwigo: ").strip().rstrip('/')
    username = input("Nom d'utilisateur: ").strip()
    password = input("Mot de passe: ").strip()
    
    album_id = None
    if len(sys.argv) > 1:
        try:
            album_id = int(sys.argv[1])
        except:
            pass
    
    if not piwigo_url or not username or not password:
        print("\n✗ Informations manquantes!")
        sys.exit(1)
    
    test_piwigo_api(piwigo_url, username, password, album_id)
