"""
Système d'automatisation Scrutart avec Prefect
Automatise le processus complet de génération de contenu pour les artistes
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path

import requests
from prefect import flow, task, get_run_logger
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import IntervalSchedule
from prefect.blocks.system import Secret
from pydantic import BaseModel


# ===== MODÈLES DE DONNÉES =====

class ArtistInfo(BaseModel):
    """Modèle pour les informations d'artiste"""
    qid: str
    name: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    nationality: Optional[str] = None
    movement: Optional[str] = None


class GenerationResult(BaseModel):
    """Résultat de génération pour un artiste"""
    qid: str
    artist_name: str
    success: bool
    steps_completed: List[str]
    errors: List[str]
    wordpress_post_id: Optional[int] = None
    piwigo_gallery_id: Optional[int] = None
    generation_time: datetime


class ProcessingBatch(BaseModel):
    """Lot de traitement d'artistes"""
    batch_id: str
    qids: List[str]
    created_at: datetime
    status: str = "pending"  # pending, processing, completed, failed
    results: List[GenerationResult] = []


# ===== CONFIGURATION =====

class ScrutartConfig:
    """Configuration centralisée pour Scrutart"""
    
    def __init__(self):
        self.wordpress_api_url = os.getenv("WORDPRESS_API_URL", "https://scrutart.grains-de-culture.fr/wp-json/wp/v2/")
        self.piwigo_url = os.getenv("PIWIGO_URL", "https://galeries.grains-de-culture.fr/")
        self.scrutart_state_url = os.getenv("SCRUTART_STATE_URL", "http://localhost:5000")
        self.wikidata_endpoint = "https://query.wikidata.org/sparql"
        
        # Chemins de fichiers
        self.base_path = Path(os.getenv("SCRUTART_BASE_PATH", "/opt/scrutart"))
        self.templates_path = self.base_path / "templates"
        self.data_path = self.base_path / "data"
        self.output_path = self.base_path / "output"
        
        # Configuration de génération
        self.supported_languages = ["fr", "en"]
        self.default_language = "fr"
        
        # Limites et timeouts
        self.request_timeout = 30
        self.max_retries = 3
        self.batch_size = 10


config = ScrutartConfig()


# ===== TÂCHES PREFECT =====

@task(name="Récupérer informations artiste", retries=3)
async def get_artist_info(qid: str) -> ArtistInfo:
    """Récupère les informations d'un artiste depuis Wikidata"""
    logger = get_run_logger()
    
    sparql_query = f"""
    SELECT ?artistLabel ?birthYear ?deathYear ?nationalityLabel ?movementLabel WHERE {{
      wd:{qid} rdfs:label ?artistLabel .
      FILTER(LANG(?artistLabel) = "fr")
      
      OPTIONAL {{
        wd:{qid} wdt:P569 ?birth .
        BIND(YEAR(?birth) AS ?birthYear)
      }}
      
      OPTIONAL {{
        wd:{qid} wdt:P570 ?death .
        BIND(YEAR(?death) AS ?deathYear)
      }}
      
      OPTIONAL {{
        wd:{qid} wdt:P27 ?nationality .
        ?nationality rdfs:label ?nationalityLabel .
        FILTER(LANG(?nationalityLabel) = "fr")
      }}
      
      OPTIONAL {{
        wd:{qid} wdt:P135 ?movement .
        ?movement rdfs:label ?movementLabel .
        FILTER(LANG(?movementLabel) = "fr")
      }}
    }}
    LIMIT 1
    """
    
    try:
        response = requests.post(
            config.wikidata_endpoint,
            data={
                'query': sparql_query,
                'format': 'json'
            },
            headers={'User-Agent': 'Scrutart/1.0'},
            timeout=config.request_timeout
        )
        response.raise_for_status()
        
        data = response.json()
        bindings = data['results']['bindings']
        
        if not bindings:
            raise ValueError(f"Aucune donnée trouvée pour {qid}")
        
        binding = bindings[0]
        
        artist_info = ArtistInfo(
            qid=qid,
            name=binding.get('artistLabel', {}).get('value', f'Artiste {qid}'),
            birth_year=int(binding.get('birthYear', {}).get('value', 0)) or None,
            death_year=int(binding.get('deathYear', {}).get('value', 0)) or None,
            nationality=binding.get('nationalityLabel', {}).get('value'),
            movement=binding.get('movementLabel', {}).get('value')
        )
        
        logger.info(f"Informations récupérées pour {artist_info.name} ({qid})")
        return artist_info
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations pour {qid}: {e}")
        raise


@task(name="Créer galerie Piwigo", retries=2)
async def create_piwigo_gallery(artist_info: ArtistInfo) -> int:
    """Crée une galerie Piwigo pour l'artiste"""
    logger = get_run_logger()
    
    try:
        # Simulation de création de galerie Piwigo
        # Dans l'implémentation réelle, utiliser l'API Piwigo
        gallery_name = artist_info.name.replace(" ", "_")
        
        # API call simulée
        gallery_data = {
            'name': artist_info.name,
            'comment': f'Œuvres de {artist_info.name} (Wikidata: {artist_info.qid})',
            'parent': 1  # Catégorie parent des artistes
        }
        
        logger.info(f"Galerie Piwigo créée pour {artist_info.name}")
        
        # Retourner un ID simulé (dans la réalité, récupérer depuis l'API)
        return hash(artist_info.qid) % 10000
        
    except Exception as e:
        logger.error(f"Erreur création galerie Piwigo pour {artist_info.qid}: {e}")
        raise


@task(name="Générer liste images", retries=2)
async def generate_image_list(artist_info: ArtistInfo) -> List[Dict]:
    """Génère la liste d'images pour l'artiste"""
    logger = get_run_logger()
    
    sparql_query = f"""
    SELECT DISTINCT ?artwork ?artworkLabel ?image WHERE {{
      ?artwork wdt:P170 wd:{artist_info.qid} ;
               wdt:P31 wd:Q3305213 ;
               wdt:P18 ?image .
      
      SERVICE wikibase:label {{ 
        bd:serviceParam wikibase:language "fr,en" . 
      }}
    }}
    LIMIT 50
    """
    
    try:
        response = requests.post(
            config.wikidata_endpoint,
            data={
                'query': sparql_query,
                'format': 'json'
            },
            headers={'User-Agent': 'Scrutart/1.0'},
            timeout=config.request_timeout
        )
        response.raise_for_status()
        
        data = response.json()
        images = []
        
        for binding in data['results']['bindings']:
            images.append({
                'artwork_qid': binding['artwork']['value'].split('/')[-1],
                'artwork_label': binding.get('artworkLabel', {}).get('value', ''),
                'image_url': binding['image']['value']
            })
        
        # Sauvegarder la liste d'images
        output_file = config.data_path / f"images_{artist_info.qid}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(images, f, indent=2, ensure_ascii=False)
        
        logger.info(f"{len(images)} images trouvées pour {artist_info.name}")
        return images
        
    except Exception as e:
        logger.error(f"Erreur génération liste images pour {artist_info.qid}: {e}")
        raise


@task(name="Uploader images Piwigo", retries=2)
async def upload_images_to_piwigo(artist_info: ArtistInfo, gallery_id: int, images: List[Dict]) -> int:
    """Upload les images vers la galerie Piwigo"""
    logger = get_run_logger()
    
    try:
        uploaded_count = 0
        
        for image in images[:10]:  # Limiter à 10 images par lot
            # Simulation d'upload
            logger.debug(f"Upload image {image['artwork_label']} vers galerie {gallery_id}")
            uploaded_count += 1
            
            # Attendre un peu entre les uploads pour éviter la surcharge
            await asyncio.sleep(0.5)
        
        logger.info(f"{uploaded_count} images uploadées pour {artist_info.name}")
        return uploaded_count
        
    except Exception as e:
        logger.error(f"Erreur upload images Piwigo pour {artist_info.qid}: {e}")
        raise


@task(name="Générer page WordPress", retries=2)
async def generate_wordpress_content(artist_info: ArtistInfo, gallery_id: int, language: str = "fr") -> str:
    """Génère le contenu de la page WordPress"""
    logger = get_run_logger()
    
    try:
        # Template de base pour la génération de contenu
        content_template = f"""
        <!-- wp:heading -->
        <h2>{artist_info.name}</h2>
        <!-- /wp:heading -->
        
        <!-- wp:paragraph -->
        <p>Analyse des œuvres de <strong>{artist_info.name}</strong> 
        {f"({artist_info.birth_year}-{artist_info.death_year})" if artist_info.birth_year else ""}
        basée sur les données Wikidata.</p>
        <!-- /wp:paragraph -->
        
        {f'<!-- wp:paragraph --><p><strong>Nationalité :</strong> {artist_info.nationality}</p><!-- /wp:paragraph -->' if artist_info.nationality else ''}
        
        {f'<!-- wp:paragraph --><p><strong>Mouvement artistique :</strong> {artist_info.movement}</p><!-- /wp:paragraph -->' if artist_info.movement else ''}
        
        <!-- wp:paragraph -->
        <p>Cette page a été générée automatiquement à partir des données disponibles sur 
        <a href="https://www.wikidata.org/entity/{artist_info.qid}">Wikidata</a>.</p>
        <!-- /wp:paragraph -->
        
        <!-- wp:paragraph -->
        <p>Découvrez les œuvres de cet artiste dans notre 
        <a href="https://galeries.grains-de-culture.fr/index.php?/category/{gallery_id}">galerie dédiée</a>.</p>
        <!-- /wp:paragraph -->
        """
        
        logger.info(f"Contenu WordPress généré pour {artist_info.name} ({language})")
        return content_template.strip()
        
    except Exception as e:
        logger.error(f"Erreur génération contenu WordPress pour {artist_info.qid}: {e}")
        raise


@task(name="Publier sur WordPress", retries=2)
async def publish_to_wordpress(artist_info: ArtistInfo, content: str, featured_image_id: Optional[int] = None) -> int:
    """Publie la page sur WordPress"""
    logger = get_run_logger()
    
    try:
        # Données de la page WordPress
        post_data = {
            'title': f'Analyse des œuvres de {artist_info.name}',
            'content': content,
            'status': 'draft',  # Publier en brouillon pour validation manuelle
            'categories': [17],  # Catégorie "Analyses d'artistes"
            'meta': {
                'wikidata_qid': artist_info.qid,
                'generated_at': datetime.now().isoformat(),
                'generation_method': 'prefect_automation'
            }
        }
        
        if featured_image_id:
            post_data['featured_media'] = featured_image_id
        
        # Simulation de publication WordPress
        # Dans l'implémentation réelle, utiliser l'API WordPress REST
        logger.info(f"Page WordPress créée pour {artist_info.name}")
        
        # Retourner un ID simulé
        post_id = hash(f"{artist_info.qid}_{datetime.now()}") % 100000
        return post_id
        
    except Exception as e:
        logger.error(f"Erreur publication WordPress pour {artist_info.qid}: {e}")
        raise


@task(name="Mettre à jour graphe d'état")
async def update_scrutart_state(artist_info: ArtistInfo, gallery_id: int, post_id: int) -> bool:
    """Met à jour le graphe d'état de Scrutart"""
    logger = get_run_logger()
    
    try:
        # Requête SPARQL UPDATE pour ajouter les informations au graphe
        update_query = f"""
        PREFIX scrutart: <https://scrutart.grains-de-culture.fr/entity/>
        PREFIX prop: <https://scrutart.grains-de-culture.fr/prop/>
        
        INSERT DATA {{
          scrutart:{artist_info.qid} prop:piwigo_gallery_id {gallery_id} ;
                                    prop:wordpress_post_id {post_id} ;
                                    prop:last_updated "{datetime.now().isoformat()}"^^xsd:dateTime ;
                                    prop:generation_status "completed" .
        }}
        """
        
        # Simulation de mise à jour du graphe
        logger.info(f"Graphe d'état mis à jour pour {artist_info.name}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur mise à jour graphe d'état pour {artist_info.qid}: {e}")
        return False


# ===== FLOW PRINCIPAL =====

@flow(name="Traitement artiste complet", log_prints=True)
async def process_artist_complete(qid: str) -> GenerationResult:
    """Flow complet pour traiter un artiste"""
    logger = get_run_logger()
    
    start_time = datetime.now()
    steps_completed = []
    errors = []
    
    try:
        # 1. Récupérer informations artiste
        logger.info(f"Début du traitement pour {qid}")
        artist_info = await get_artist_info(qid)
        steps_completed.append("artist_info")
        
        # 2. Créer galerie Piwigo
        gallery_id = await create_piwigo_gallery(artist_info)
        steps_completed.append("piwigo_gallery")
        
        # 3. Générer liste d'images
        images = await generate_image_list(artist_info)
        steps_completed.append("image_list")
        
        # 4. Upload images vers Piwigo
        uploaded_count = await upload_images_to_piwigo(artist_info, gallery_id, images)
        steps_completed.append("piwigo_upload")
        
        # 5. Générer contenu WordPress
        wp_content = await generate_wordpress_content(artist_info, gallery_id)
        steps_completed.append("wordpress_content")
        
        # 6. Publier sur WordPress
        post_id = await publish_to_wordpress(artist_info, wp_content)
        steps_completed.append("wordpress_publish")
        
        # 7. Mettre à jour graphe d'état
        state_updated = await update_scrutart_state(artist_info, gallery_id, post_id)
        if state_updated:
            steps_completed.append("scrutart_state")
        
        # Créer le résultat
        result = GenerationResult(
            qid=qid,
            artist_name=artist_info.name,
            success=True,
            steps_completed=steps_completed,
            errors=errors,
            wordpress_post_id=post_id,
            piwigo_gallery_id=gallery_id,
            generation_time=datetime.now() - start_time
        )
        
        logger.info(f"Traitement terminé avec succès pour {artist_info.name}")
        return result
        
    except Exception as e:
        error_msg = f"Erreur lors du traitement de {qid}: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        
        return GenerationResult(
            qid=qid,
            artist_name=f"Artiste {qid}",
            success=False,
            steps_completed=steps_completed,
            errors=errors,
            generation_time=datetime.now() - start_time
        )


@flow(name="Traitement par lots", log_prints=True)
async def process_artists_batch(qids: List[str], batch_id: Optional[str] = None) -> List[GenerationResult]:
    """Traite un lot d'artistes"""
    logger = get_run_logger()
    
    if not batch_id:
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"Début du traitement du lot {batch_id} avec {len(qids)} artistes")
    
    # Traiter les artistes en parallèle avec une limite de concurrence
    semaphore = asyncio.Semaphore(config.batch_size)
    
    async def process_with_semaphore(qid: str) -> GenerationResult:
        async with semaphore:
            return await process_artist_complete(qid)
    
    # Lancer tous les traitements
    results = await asyncio.gather(
        *[process_with_semaphore(qid) for qid in qids],
        return_exceptions=True
    )
    
    # Traiter les résultats et exceptions
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            error_result = GenerationResult(
                qid=qids[i],
                artist_name=f"Artiste {qids[i]}",
                success=False,
                steps_completed=[],
                errors=[str(result)],
                generation_time=timedelta(seconds=0)
            )
            final_results.append(error_result)
        else:
            final_results.append(result)
    
    # Statistiques du lot
    successful = sum(1 for r in final_results if r.success)
    failed = len(final_results) - successful
    
    logger.info(f"Lot {batch_id} terminé: {successful} succès, {failed} échecs")
    
    return final_results


# ===== DÉPLOIEMENT =====

def create_deployment():
    """Crée le déploiement Prefect"""
    
    deployment = Deployment.build_from_flow(
        flow=process_artists_batch,
        name="scrutart-batch-processing",
        version="1.0.0",
        description="Traitement par lots d'artistes Scrutart",
        tags=["scrutart", "artists", "automation"],
        schedule=IntervalSchedule(interval=timedelta(hours=6)),  # Toutes les 6 heures
        work_pool_name="default-agent-pool"
    )
    
    return deployment


if __name__ == "__main__":
    # Exemple d'utilisation
    import asyncio
    
    # Test avec un seul artiste
    qid_test = "Q296"  # Claude Monet
    result = asyncio.run(process_artist_complete(qid_test))
    print(f"Résultat: {result}")
    
    # Test avec un lot
    qids_test = ["Q296", "Q5582", "Q5597"]  # Monet, Van Gogh, Cézanne
    batch_results = asyncio.run(process_artists_batch(qids_test))
    print(f"Résultats du lot: {len(batch_results)} artistes traités")