"""
Binary Data Module (BDM) for JFA Microservice

This module handles binary data operations:
- Binary data generation from validated templates
- Data compression and encoding
- Binary data analysis and validation
- Checksum generation and verification
- Binary format conversion and processing
"""

import logging
import asyncio
import struct
import gzip
import zlib
import hashlib
import base64
import json
import tempfile
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import io


class BinaryDataModule:
    """
    Binary Data Module
    
    Handles binary data generation, compression, and analysis
    for JFA template processing workflows.
    """
    
    def __init__(self):
        """Initialize the BDM module."""
        self.logger = logging.getLogger(__name__)
        self.module_name = "BDM"
        self.is_active = False
        
        # Binary processing configuration
        self.binary_config = {
            "default_compression": "gzip",
            "compression_level": 6,
            "encoding": "utf-8",
            "enable_checksum": True,
            "checksum_algorithm": "sha256",
            "max_binary_size": 50 * 1024 * 1024,  # 50MB
            "version_control": True,
            "binary_format_version": "1.0"
        }
        
        # Binary data formats
        self.binary_formats = {
            "standard": self._generate_standard_binary,
            "compressed": self._generate_compressed_binary,
            "structured": self._generate_structured_binary,
            "legacy": self._generate_legacy_binary
        }
        
        # Compression algorithms
        self.compression_algorithms = {
            "gzip": gzip.compress,
            "zlib": zlib.compress,
            "none": lambda x: x
        }
        
        # Decompression algorithms
        self.decompression_algorithms = {
            "gzip": gzip.decompress,
            "zlib": zlib.decompress,
            "none": lambda x: x
        }
        
        # Processing statistics
        self.stats = {
            "total_generated": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "total_analyzed": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "total_bytes_processed": 0,
            "average_generation_time": 0.0,
            "last_activity": None
        }
        
        # Binary processing metrics
        self.binary_metrics = {
            "generation_success_rate": 0.0,
            "analysis_success_rate": 0.0,
            "average_binary_size": 0.0,
            "compression_ratio": 0.0,
            "processing_speed": 0.0,
            "format_distribution": {},
            "compression_effectiveness": 0.0
        }
        
        self.logger.info(f"{self.module_name} initialized successfully")
    
    async def start(self):
        """Start the BDM module."""
        try:
            self.is_active = True
            self.logger.info(f"{self.module_name} started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start {self.module_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the BDM module."""
        try:
            self.is_active = False
            self.logger.info(f"{self.module_name} stopped successfully")
        except Exception as e:
            self.logger.error(f"Failed to stop {self.module_name}: {e}")
            raise
    
    async def generate_binary_data(self, validated_data: Dict[str, Any], 
                                  format_type: str = "standard") -> Dict[str, Any]:
        """
        Generate binary data from validated template data.
        
        Args:
            validated_data: Validated template data
            format_type: Binary format type (standard, compressed, structured, legacy)
            
        Returns:
            Binary generation result
        """
        try:
            start_time = datetime.now()
            self.stats["total_generated"] += 1
            
            # Step 1: Select binary format generator
            if format_type not in self.binary_formats:
                format_type = "standard"
            
            generator = self.binary_formats[format_type]
            
            # Step 2: Check size limits
            data_size = len(str(validated_data))
            if data_size > self.binary_config["max_binary_size"]:
                self.stats["failed_generations"] += 1
                return {
                    "success": False,
                    "error": f"Data size {data_size} exceeds maximum allowed size {self.binary_config['max_binary_size']}",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Step 3: Generate binary data
            binary_result = await generator(validated_data)
            
            if not binary_result["success"]:
                self.stats["failed_generations"] += 1
                return binary_result
            
            # Step 3: Add metadata and checksums
            binary_data = binary_result["binary_data"]
            metadata = await self._generate_binary_metadata(binary_data, format_type, validated_data)
            
            # Step 4: Generate checksum if enabled
            checksum = None
            if self.binary_config["enable_checksum"]:
                checksum = await self._generate_checksum(binary_data)
            
            # Step 5: Create final binary package
            binary_package = await self._create_binary_package(
                binary_data, metadata, checksum, format_type
            )
            
            # Step 6: Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.bin')
            file_path = temp_file.name
            temp_file.write(binary_data)
            temp_file.close()
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            self.stats["successful_generations"] += 1
            self.stats["total_bytes_processed"] += len(binary_data)
            self.stats["last_activity"] = datetime.now()
            
            # Update metrics
            await self._update_binary_metrics(binary_data, processing_time, format_type)
            
            return {
                "success": True,
                "binary_data": binary_package["binary_data"],
                "binary_metadata": binary_package["metadata"],
                "checksum": checksum,
                "file_path": file_path,
                "format_type": format_type,
                "size": len(binary_data),
                "processing_time": processing_time,
                "generation_stats": {
                    "original_size": len(str(validated_data)),
                    "binary_size": len(binary_data),
                    "compression_ratio": len(str(validated_data)) / len(binary_data) if len(binary_data) > 0 else 0,
                    "format": format_type
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating binary data: {e}")
            self.stats["failed_generations"] += 1
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _generate_standard_binary(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate standard binary format."""
        try:
            # Create binary structure
            binary_data = bytearray()
            
            # Add header
            header = self._create_binary_header("standard", validated_data)
            binary_data.extend(header)
            
            # Add JFA data sections
            if "jfa_data" in validated_data:
                jfa_data = validated_data["jfa_data"]
                
                # Add flag data
                if "flag" in jfa_data:
                    flag_binary = self._encode_flag_data(jfa_data["flag"])
                    binary_data.extend(flag_binary)
                
                # Add location data
                if "loca" in jfa_data:
                    loca_binary = self._encode_location_data(jfa_data["loca"])
                    binary_data.extend(loca_binary)
                
                # Add customer data
                if "cust" in jfa_data:
                    cust_binary = self._encode_customer_data(jfa_data["cust"])
                    binary_data.extend(cust_binary)
                
                # Add solar information data
                if "sinf" in jfa_data:
                    sinf_binary = self._encode_metadata_payload(jfa_data["sinf"])
                    binary_data.extend(sinf_binary)
            
            # Add footer
            footer = self._create_binary_footer()
            binary_data.extend(footer)
            
            return {
                "success": True,
                "binary_data": bytes(binary_data),
                "format": "standard"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Standard binary generation error: {str(e)}"
            }
    
    async def _generate_compressed_binary(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate compressed binary format."""
        try:
            # First generate standard binary
            standard_result = await self._generate_standard_binary(validated_data)
            
            if not standard_result["success"]:
                return standard_result
            
            # Apply compression
            compression_type = self.binary_config["default_compression"]
            if compression_type in self.compression_algorithms:
                compressor = self.compression_algorithms[compression_type]
                
                if compression_type == "gzip":
                    compressed_data = compressor(standard_result["binary_data"], 
                                               compresslevel=self.binary_config["compression_level"])
                elif compression_type == "zlib":
                    compressed_data = compressor(standard_result["binary_data"], 
                                               level=self.binary_config["compression_level"])
                else:
                    compressed_data = compressor(standard_result["binary_data"])
            else:
                compressed_data = standard_result["binary_data"]
            
            return {
                "success": True,
                "binary_data": compressed_data,
                "format": "compressed",
                "compression_type": compression_type,
                "original_size": len(standard_result["binary_data"]),
                "compressed_size": len(compressed_data)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Compressed binary generation error: {str(e)}"
            }
    
    async def _generate_structured_binary(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured binary format with sections."""
        try:
            # Create structured binary with clear sections
            binary_data = bytearray()
            
            # Add structured header
            header = self._create_structured_header(validated_data)
            binary_data.extend(header)
            
            # Add section table
            sections = []
            section_data = bytearray()
            
            # Template info section
            template_section = self._create_template_section(validated_data)
            sections.append(("TEMPLATE", len(section_data), len(template_section)))
            section_data.extend(template_section)
            
            # JFA data sections
            if "jfa_data" in validated_data:
                jfa_data = validated_data["jfa_data"]
                
                for section_name, section_key in [("FLAG", "flag"), ("LOCATION", "loca"), 
                                                ("CUSTOMER", "cust"), ("SOLAR", "sinf")]:
                    if section_key in jfa_data:
                        section_binary = self._create_jfa_section(section_name, jfa_data[section_key])
                        sections.append((section_name, len(section_data), len(section_binary)))
                        section_data.extend(section_binary)
            
            # Add section table to binary
            section_table = self._create_section_table(sections)
            binary_data.extend(section_table)
            
            # Add section data
            binary_data.extend(section_data)
            
            # Add structured footer
            footer = self._create_structured_footer()
            binary_data.extend(footer)
            
            return {
                "success": True,
                "binary_data": bytes(binary_data),
                "format": "structured",
                "sections": [section[0] for section in sections]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Structured binary generation error: {str(e)}"
            }
    
    async def _generate_legacy_binary(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate legacy binary format for backward compatibility."""
        try:
            # Create legacy binary structure
            binary_data = bytearray()
            
            # Legacy header (simple format)
            binary_data.extend(b"JFA1")  # Magic number
            binary_data.extend(struct.pack(">I", int(datetime.now().timestamp())))
            
            # Convert to JSON and encode
            json_data = json.dumps(validated_data, ensure_ascii=False)
            json_bytes = json_data.encode(self.binary_config["encoding"])
            
            # Add length and data
            binary_data.extend(struct.pack(">I", len(json_bytes)))
            binary_data.extend(json_bytes)
            
            # Simple checksum (CRC32)
            checksum = zlib.crc32(json_bytes) & 0xffffffff
            binary_data.extend(struct.pack(">I", checksum))
            
            return {
                "success": True,
                "binary_data": bytes(binary_data),
                "format": "legacy"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Legacy binary generation error: {str(e)}"
            }
    
    def _create_binary_header(self, format_type: str, validated_data: Dict[str, Any]) -> bytes:
        """Create binary header."""
        header = bytearray()
        
        # Magic number
        header.extend(b"JFA2")
        
        # Format type
        format_bytes = format_type.encode('ascii')[:8].ljust(8, b'\x00')
        header.extend(format_bytes)
        
        # Version
        header.extend(struct.pack(">H", 1))  # Version 1
        
        # Timestamp
        header.extend(struct.pack(">I", int(datetime.now().timestamp())))
        
        # Template ID
        template_id = validated_data.get("id", "unknown")[:16]
        id_bytes = template_id.encode('ascii')[:16].ljust(16, b'\x00')
        header.extend(id_bytes)
        
        # Flags
        flags = 0
        if "jfa_data" in validated_data:
            flags |= 0x01
        if self.binary_config["enable_checksum"]:
            flags |= 0x02
        if self.binary_config["version_control"]:
            flags |= 0x04
        header.extend(struct.pack(">H", flags))
        
        return bytes(header)
    
    def _create_binary_footer(self) -> bytes:
        """Create binary footer."""
        footer = bytearray()
        
        # End marker
        footer.extend(b"END2")
        
        # Timestamp
        footer.extend(struct.pack(">I", int(datetime.now().timestamp())))
        
        return bytes(footer)
    
    def _encode_flag_data(self, flag_data: Dict[str, Any]) -> bytes:
        """Encode flag data to binary."""
        flag_bytes = bytearray()
        
        # Section header
        flag_bytes.extend(b"FLAG")
        flag_bytes.extend(struct.pack(">H", 28))  # Section length
        
        # Flag values
        flag_fields = ["vald", "calc", "plat", "mpsz", "econ", "rcon", "mode"]
        for field in flag_fields:
            value = flag_data.get(field, 0)
            flag_bytes.extend(struct.pack(">I", value))
        
        return bytes(flag_bytes)
    
    def _encode_location_data(self, loca_data: Dict[str, Any]) -> bytes:
        """Encode location data to binary."""
        loca_bytes = bytearray()
        
        # Section header
        loca_bytes.extend(b"LOCA")
        
        # Encode strings
        ecit = loca_data.get("Ecit", "").encode('utf-8')[:100]
        fcit = loca_data.get("Fcit", "").encode('utf-8')[:100]
        
        # Calculate section length
        section_length = 4 + 4 + 8 + 8 + len(ecit) + len(fcit)
        loca_bytes.extend(struct.pack(">H", section_length))
        
        # String lengths and data
        loca_bytes.extend(struct.pack(">H", len(ecit)))
        loca_bytes.extend(ecit)
        loca_bytes.extend(struct.pack(">H", len(fcit)))
        loca_bytes.extend(fcit)
        
        # Coordinates
        lat = float(loca_data.get("lat", 0.0))
        lng = float(loca_data.get("lng", 0.0))
        loca_bytes.extend(struct.pack(">d", lat))
        loca_bytes.extend(struct.pack(">d", lng))
        
        return bytes(loca_bytes)
    
    def _encode_customer_data(self, cust_data: Dict[str, Any]) -> bytes:
        """Encode customer data to binary."""
        cust_bytes = bytearray()
        
        # Section header
        cust_bytes.extend(b"CUST")
        cust_bytes.extend(struct.pack(">H", 12))  # Section length
        
        # Customer values
        mode = cust_data.get("mode", 0)
        need = cust_data.get("need", 0)
        npsz = cust_data.get("npsz", 0)
        
        cust_bytes.extend(struct.pack(">I", mode))
        cust_bytes.extend(struct.pack(">I", need))
        cust_bytes.extend(struct.pack(">I", npsz))
        
        return bytes(cust_bytes)
    
    def _encode_metadata_payload(self, metadata: Dict[str, Any]) -> bytes:
        """Encode optional metadata section to binary."""
        sinf_bytes = bytearray()
        
        # Section header
        sinf_bytes.extend(b"SINF")
        sinf_bytes.extend(struct.pack(">H", 96))  # Section length (24 fields * 4 bytes)
        
        # Solar information fields
        sinf_fields = [
            "mfreg", "mled", "mlcd", "mtele", "mlamp", "mpump", "mcool", "mcamd",
            "mpc", "mpri", "mwel", "mmlo", "nfreg", "nled", "nlcd", "ntele",
            "nlamp", "npump", "ncool", "ncamd", "npc", "npri", "nwel", "nmlo"
        ]
        
        for field in sinf_fields:
            value = metadata.get(field, 0)
            sinf_bytes.extend(struct.pack(">I", value))
        
        return bytes(sinf_bytes)

    _encode_solar_info_data = _encode_metadata_payload
    
    def _create_structured_header(self, validated_data: Dict[str, Any]) -> bytes:
        """Create structured binary header."""
        header = bytearray()
        
        # Magic number for structured format
        header.extend(b"JFS2")
        
        # Version
        header.extend(struct.pack(">H", 1))
        
        # Timestamp
        header.extend(struct.pack(">I", int(datetime.now().timestamp())))
        
        # Template info
        template_id = validated_data.get("id", "unknown")[:32]
        id_bytes = template_id.encode('utf-8')[:32].ljust(32, b'\x00')
        header.extend(id_bytes)
        
        return bytes(header)
    
    def _create_template_section(self, validated_data: Dict[str, Any]) -> bytes:
        """Create template section."""
        section = bytearray()
        
        # Basic template info
        template_info = {
            "id": validated_data.get("id", ""),
            "object": validated_data.get("object", ""),
            "created": validated_data.get("created", 0),
            "model": validated_data.get("model", "")
        }
        
        # Convert to JSON and encode
        json_data = json.dumps(template_info, ensure_ascii=False)
        json_bytes = json_data.encode('utf-8')
        
        section.extend(struct.pack(">I", len(json_bytes)))
        section.extend(json_bytes)
        
        return bytes(section)
    
    def _create_jfa_section(self, section_name: str, section_data: Dict[str, Any]) -> bytes:
        """Create JFA data section."""
        section = bytearray()
        
        # Convert section data to JSON
        json_data = json.dumps(section_data, ensure_ascii=False)
        json_bytes = json_data.encode('utf-8')
        
        # Add section name
        name_bytes = section_name.encode('ascii')[:8].ljust(8, b'\x00')
        section.extend(name_bytes)
        
        # Add data length and data
        section.extend(struct.pack(">I", len(json_bytes)))
        section.extend(json_bytes)
        
        return bytes(section)
    
    def _create_section_table(self, sections: List[tuple]) -> bytes:
        """Create section table."""
        table = bytearray()
        
        # Number of sections
        table.extend(struct.pack(">H", len(sections)))
        
        # Section entries
        for name, offset, size in sections:
            name_bytes = name.encode('ascii')[:8].ljust(8, b'\x00')
            table.extend(name_bytes)
            table.extend(struct.pack(">I", offset))
            table.extend(struct.pack(">I", size))
        
        return bytes(table)
    
    def _create_structured_footer(self) -> bytes:
        """Create structured binary footer."""
        footer = bytearray()
        
        # End marker
        footer.extend(b"ENDS")
        
        # Timestamp
        footer.extend(struct.pack(">I", int(datetime.now().timestamp())))
        
        return bytes(footer)
    
    async def _generate_binary_metadata(self, binary_data: bytes, format_type: str, 
                                      validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate binary metadata."""
        try:
            metadata = {
                "format": format_type,
                "version": self.binary_config["binary_format_version"],
                "size": len(binary_data),
                "encoding": self.binary_config["encoding"],
                "compression": self.binary_config["default_compression"],
                "created": datetime.now().isoformat(),
                "template_id": validated_data.get("id", "unknown"),
                "template_model": validated_data.get("model", "unknown"),
                "jfa_sections": []
            }
            
            # Add JFA section information
            if "jfa_data" in validated_data:
                jfa_data = validated_data["jfa_data"]
                metadata["jfa_sections"] = list(jfa_data.keys())
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error generating binary metadata: {e}")
            return {}
    
    async def _generate_checksum(self, binary_data: bytes) -> str:
        """Generate checksum for binary data."""
        try:
            algorithm = self.binary_config["checksum_algorithm"]
            
            if algorithm == "sha256":
                hash_obj = hashlib.sha256(binary_data)
            elif algorithm == "md5":
                hash_obj = hashlib.md5(binary_data)
            else:
                hash_obj = hashlib.sha256(binary_data)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Error generating checksum: {e}")
            return ""
    
    async def _create_binary_package(self, binary_data: bytes, metadata: Dict[str, Any], 
                                   checksum: str, format_type: str) -> Dict[str, Any]:
        """Create final binary package."""
        try:
            package = {
                "binary_data": binary_data,
                "metadata": metadata
            }
            
            if checksum:
                package["metadata"]["checksum"] = checksum
            
            return package
            
        except Exception as e:
            self.logger.error(f"Error creating binary package: {e}")
            return {"binary_data": binary_data, "metadata": metadata}
    
    async def analyze_binary_data(self, binary_data: bytes) -> Dict[str, Any]:
        """
        Analyze binary data.
        
        Args:
            binary_data: Binary data to analyze
            
        Returns:
            Analysis result
        """
        try:
            start_time = datetime.now()
            self.stats["total_analyzed"] += 1
            
            # Detect format
            format_detection = await self._detect_binary_format(binary_data)
            
            # Analyze structure
            structure_analysis = await self._analyze_binary_structure(binary_data, format_detection["format"])
            
            # Validate integrity
            integrity_check = await self._validate_binary_integrity(binary_data, format_detection["format"])
            
            # Extract metadata
            metadata_extraction = await self._extract_binary_metadata(binary_data, format_detection["format"])
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            self.stats["successful_analyses"] += 1
            self.stats["last_activity"] = datetime.now()
            
            return {
                "success": True,
                "format_detection": format_detection,
                "structure_analysis": structure_analysis,
                "integrity_check": integrity_check,
                "metadata": metadata_extraction,
                "analysis_time": processing_time,
                "size": len(binary_data),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing binary data: {e}")
            self.stats["failed_analyses"] += 1
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _detect_binary_format(self, binary_data: bytes) -> Dict[str, Any]:
        """Detect binary format."""
        try:
            if len(binary_data) < 4:
                return {"format": "unknown", "confidence": 0.0}
            
            # Check magic numbers
            magic = binary_data[:4]
            
            if magic == b"JFA2":
                return {"format": "standard", "confidence": 1.0}
            elif magic == b"JFS2":
                return {"format": "structured", "confidence": 1.0}
            elif magic == b"JFA1":
                return {"format": "legacy", "confidence": 1.0}
            elif magic[:2] == b"\x1f\x8b":  # gzip magic
                return {"format": "compressed", "confidence": 0.8}
            else:
                return {"format": "unknown", "confidence": 0.0}
                
        except Exception as e:
            return {"format": "unknown", "confidence": 0.0, "error": str(e)}
    
    async def _analyze_binary_structure(self, binary_data: bytes, format_type: str) -> Dict[str, Any]:
        """Analyze binary structure."""
        try:
            structure = {
                "format": format_type,
                "size": len(binary_data),
                "sections": [],
                "valid_structure": False
            }
            
            if format_type == "standard":
                structure.update(await self._analyze_standard_structure(binary_data))
            elif format_type == "structured":
                structure.update(await self._analyze_structured_structure(binary_data))
            elif format_type == "legacy":
                structure.update(await self._analyze_legacy_structure(binary_data))
            elif format_type == "compressed":
                structure.update(await self._analyze_compressed_structure(binary_data))
            
            return structure
            
        except Exception as e:
            return {"format": format_type, "size": len(binary_data), "error": str(e)}
    
    async def _analyze_standard_structure(self, binary_data: bytes) -> Dict[str, Any]:
        """Analyze standard binary structure."""
        try:
            sections = []
            offset = 0
            
            # Parse header
            if len(binary_data) >= 42:
                header = binary_data[offset:offset+42]
                sections.append({"name": "header", "offset": offset, "size": 42})
                offset += 42
            
            # Parse sections
            while offset < len(binary_data) - 8:
                if offset + 6 > len(binary_data):
                    break
                
                section_type = binary_data[offset:offset+4]
                section_size = struct.unpack(">H", binary_data[offset+4:offset+6])[0]
                
                if section_type == b"END2":
                    sections.append({"name": "footer", "offset": offset, "size": 8})
                    break
                
                sections.append({
                    "name": section_type.decode('ascii', errors='ignore'),
                    "offset": offset,
                    "size": section_size + 6
                })
                offset += section_size + 6
            
            return {
                "sections": sections,
                "valid_structure": len(sections) > 0
            }
            
        except Exception as e:
            return {"sections": [], "valid_structure": False, "error": str(e)}
    
    async def _analyze_structured_structure(self, binary_data: bytes) -> Dict[str, Any]:
        """Analyze structured binary structure."""
        try:
            sections = []
            
            # Parse header
            if len(binary_data) >= 42:
                sections.append({"name": "header", "offset": 0, "size": 42})
            
            # Parse section table
            if len(binary_data) >= 44:
                num_sections = struct.unpack(">H", binary_data[42:44])[0]
                table_size = 2 + num_sections * 16
                sections.append({"name": "section_table", "offset": 42, "size": table_size})
                
                # Parse individual sections
                for i in range(num_sections):
                    entry_offset = 44 + i * 16
                    section_name = binary_data[entry_offset:entry_offset+8].decode('ascii', errors='ignore').strip('\x00')
                    data_offset = struct.unpack(">I", binary_data[entry_offset+8:entry_offset+12])[0]
                    data_size = struct.unpack(">I", binary_data[entry_offset+12:entry_offset+16])[0]
                    
                    sections.append({
                        "name": section_name,
                        "offset": 42 + table_size + data_offset,
                        "size": data_size
                    })
            
            return {
                "sections": sections,
                "valid_structure": len(sections) > 2
            }
            
        except Exception as e:
            return {"sections": [], "valid_structure": False, "error": str(e)}
    
    async def _analyze_legacy_structure(self, binary_data: bytes) -> Dict[str, Any]:
        """Analyze legacy binary structure."""
        try:
            sections = []
            
            if len(binary_data) >= 16:
                # Header
                sections.append({"name": "header", "offset": 0, "size": 12})
                
                # Data length
                data_length = struct.unpack(">I", binary_data[8:12])[0]
                sections.append({"name": "data", "offset": 12, "size": data_length})
                
                # Checksum
                sections.append({"name": "checksum", "offset": 12 + data_length, "size": 4})
            
            return {
                "sections": sections,
                "valid_structure": len(sections) == 3
            }
            
        except Exception as e:
            return {"sections": [], "valid_structure": False, "error": str(e)}
    
    async def _analyze_compressed_structure(self, binary_data: bytes) -> Dict[str, Any]:
        """Analyze compressed binary structure."""
        try:
            # Try to decompress
            try:
                decompressed = gzip.decompress(binary_data)
                inner_analysis = await self._analyze_binary_structure(decompressed, "standard")
                
                return {
                    "sections": [{"name": "compressed_data", "offset": 0, "size": len(binary_data)}],
                    "valid_structure": True,
                    "inner_structure": inner_analysis,
                    "compression_ratio": len(decompressed) / len(binary_data)
                }
                
            except Exception:
                return {"sections": [], "valid_structure": False, "error": "Invalid gzip data"}
                
        except Exception as e:
            return {"sections": [], "valid_structure": False, "error": str(e)}
    
    async def _validate_binary_integrity(self, binary_data: bytes, format_type: str) -> Dict[str, Any]:
        """Validate binary integrity."""
        try:
            integrity_result = {
                "valid": True,
                "checks": [],
                "errors": []
            }
            
            # Size check
            if len(binary_data) == 0:
                integrity_result["valid"] = False
                integrity_result["errors"].append("Empty binary data")
            else:
                integrity_result["checks"].append("size_check")
            
            # Format-specific checks
            if format_type == "standard":
                # Check magic number
                if len(binary_data) >= 4 and binary_data[:4] == b"JFA2":
                    integrity_result["checks"].append("magic_number")
                else:
                    integrity_result["valid"] = False
                    integrity_result["errors"].append("Invalid magic number")
                
                # Check footer
                if len(binary_data) >= 8 and binary_data[-8:-4] == b"END2":
                    integrity_result["checks"].append("footer")
                else:
                    integrity_result["valid"] = False
                    integrity_result["errors"].append("Invalid footer")
            
            elif format_type == "legacy":
                # Check legacy format
                if len(binary_data) >= 16:
                    data_length = struct.unpack(">I", binary_data[8:12])[0]
                    expected_size = 16 + data_length
                    
                    if len(binary_data) == expected_size:
                        integrity_result["checks"].append("size_consistency")
                    else:
                        integrity_result["valid"] = False
                        integrity_result["errors"].append("Size inconsistency")
                    
                    # Check checksum
                    if len(binary_data) >= 16 + data_length:
                        data_section = binary_data[12:12+data_length]
                        stored_checksum = struct.unpack(">I", binary_data[12+data_length:16+data_length])[0]
                        calculated_checksum = zlib.crc32(data_section) & 0xffffffff
                        
                        if stored_checksum == calculated_checksum:
                            integrity_result["checks"].append("checksum")
                        else:
                            integrity_result["valid"] = False
                            integrity_result["errors"].append("Checksum mismatch")
            
            return integrity_result
            
        except Exception as e:
            return {
                "valid": False,
                "checks": [],
                "errors": [f"Integrity check error: {str(e)}"]
            }
    
    async def _extract_binary_metadata(self, binary_data: bytes, format_type: str) -> Dict[str, Any]:
        """Extract metadata from binary data."""
        try:
            metadata = {
                "format": format_type,
                "size": len(binary_data),
                "extraction_time": datetime.now().isoformat()
            }
            
            if format_type == "standard" and len(binary_data) >= 42:
                # Extract from header
                metadata["version"] = struct.unpack(">H", binary_data[12:14])[0]
                metadata["timestamp"] = struct.unpack(">I", binary_data[14:18])[0]
                metadata["template_id"] = binary_data[18:34].decode('ascii', errors='ignore').strip('\x00')
                metadata["flags"] = struct.unpack(">H", binary_data[34:36])[0]
            
            elif format_type == "legacy" and len(binary_data) >= 12:
                # Extract from legacy header
                metadata["timestamp"] = struct.unpack(">I", binary_data[4:8])[0]
            
            return metadata
            
        except Exception as e:
            return {
                "format": format_type,
                "size": len(binary_data),
                "error": str(e)
            }
    
    async def _update_binary_metrics(self, binary_data: bytes, processing_time: float, format_type: str):
        """Update binary processing metrics."""
        try:
            # Update success rate
            total_generated = self.stats["total_generated"]
            if total_generated > 0:
                self.binary_metrics["generation_success_rate"] = (
                    self.stats["successful_generations"] / total_generated
                )
            
            # Update average binary size
            current_avg_size = self.binary_metrics["average_binary_size"]
            binary_size = len(binary_data)
            self.binary_metrics["average_binary_size"] = (
                (current_avg_size * (total_generated - 1) + binary_size) / total_generated
            )
            
            # Update processing speed
            current_speed = self.binary_metrics["processing_speed"]
            new_speed = binary_size / processing_time if processing_time > 0 else 0
            self.binary_metrics["processing_speed"] = (
                (current_speed * (total_generated - 1) + new_speed) / total_generated
            )
            
            # Update format distribution
            self.binary_metrics["format_distribution"][format_type] = (
                self.binary_metrics["format_distribution"].get(format_type, 0) + 1
            )
            
            # Update average generation time
            current_avg_time = self.stats["average_generation_time"]
            self.stats["average_generation_time"] = (
                (current_avg_time * (total_generated - 1) + processing_time) / total_generated
            )
            
        except Exception as e:
            self.logger.error(f"Error updating binary metrics: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the BDM module."""
        return {
            "module": self.module_name,
            "is_active": self.is_active,
            "statistics": self.stats,
            "binary_metrics": self.binary_metrics,
            "configuration": self.binary_config,
            "supported_formats": list(self.binary_formats.keys()),
            "compression_algorithms": list(self.compression_algorithms.keys()),
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test binary generation
            test_data = {
                "id": "test-001",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": "gpt-4",
                "jfa_data": {
                    "flag": {"vald": 1, "calc": 1, "plat": 1, "mpsz": 1, "econ": 1, "rcon": 0, "mode": 1},
                    "loca": {"Ecit": "tehran", "Fcit": "تهران", "lat": 35.6892, "lng": 51.3889},
                    "cust": {"mode": 1, "need": 1, "npsz": 5},
                    "sinf": {"mfreg": 1, "mled": 1, "mlcd": 1, "mtele": 1, "mlamp": 1, "mpump": 1}
                }
            }
            
            start_time = datetime.now()
            result = await self.generate_binary_data(test_data)
            test_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "healthy": self.is_active and result["success"],
                "module": self.module_name,
                "timestamp": datetime.now().isoformat(),
                "test_performance": test_time,
                "binary_capabilities": {
                    "generation": True,
                    "compression": True,
                    "analysis": True,
                    "multiple_formats": True
                },
                "statistics": self.stats
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "module": self.module_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 