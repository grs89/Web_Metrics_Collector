import geoip2.database
import os
import logging

class GeoIPEnricher:
    def __init__(self, db_path='GeoLite2-City.mmdb'):
        self.reader = None
        self.license_key = os.getenv('GEOIP_LICENSE_KEY')
        
        if not os.path.exists(db_path) and self.license_key:
            self._download_db(db_path)

        if os.path.exists(db_path):
            try:
                self.reader = geoip2.database.Reader(db_path)
                logging.info(f"Loaded GeoIP database from {db_path}")
            except Exception as e:
                logging.error(f"Failed to load GeoIP database: {e}")
        else:
            logging.warning(f"GeoIP database not found at {db_path}. Geolocation will be disabled.")
    
    def _download_db(self, db_path):
        import requests
        import tarfile
        import shutil
        
        logging.info("Downloading GeoLite2-City database...")
        url = f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={self.license_key}&suffix=tar.gz"
        
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                # Save tar.gz
                tar_path = f"{db_path}.tar.gz"
                with open(tar_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        f.write(chunk)
                
                # Extract
                with tarfile.open(tar_path, "r:gz") as tar:
                    for member in tar.getmembers():
                        if member.name.endswith('.mmdb'):
                            member.name = os.path.basename(member.name) # flattened
                            tar.extract(member, path=".")
                            # Rename if needed (tar extract naming varies)
                            # Actually simpler: extract specific file to db_path
                            extracted_file = tar.extractfile(member)
                            with open(db_path, 'wb') as out:
                                shutil.copyfileobj(extracted_file, out)
                            break
                            
                os.remove(tar_path)
                logging.info("GeoIP database downloaded successfully.")
            else:
                logging.error(f"Failed to download GeoIP DB: HTTP {response.status_code}")
        except Exception as e:
            logging.error(f"Error downloading GeoIP DB: {e}")

    async def enrich(self, ip_address):
        if not self.reader or not ip_address:
            return {}

        try:
            # MaxMind's reader is blocking, so we run it in a thread to keep the event loop alive
            import asyncio
            response = await asyncio.to_thread(self.reader.city, ip_address)
            return {
                'country_code': response.country.iso_code,
                'city': response.city.name,
                'latitude': response.location.latitude,
                'longitude': response.location.longitude
            }
        except geoip2.errors.AddressNotFoundError:
            return {}
        except Exception as e:
            logging.debug(f"GeoIP lookup error for {ip_address}: {e}")
            return {}

    def close(self):
        if self.reader:
            self.reader.close()
