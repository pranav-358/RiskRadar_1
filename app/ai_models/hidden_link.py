import networkx as nx
import pandas as pd
import numpy as np
from collections import defaultdict, deque
import logging
from datetime import datetime, timedelta
import json
import joblib
import os
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import community as community_louvain  # python-louvain package
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HiddenLinkAI:
    def __init__(self):
        self.graph = nx.Graph()
        self.entity_nodes = set()
        self.known_fraudulent_entities = set()
        self.communities = {}
        self.centrality_scores = {}
        self.model_path = os.path.join(os.path.dirname(__file__), '../../models/hidden_link_model.joblib')
        self.graph_path = os.path.join(os.path.dirname(__file__), '../../models/fraud_graph.gexf')
        
        # Create models directory if it doesn't exist
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        # Load known fraudulent patterns
        self._load_known_patterns()
        logger.info("Hidden Link AI initialized")
    
    def _load_known_patterns(self):
        """Load known fraudulent entity patterns"""
        # In production, this would come from a database
        self.known_fraudulent_entities = {
            # Example known fraudulent phone numbers, addresses, etc.
            "PHONE_+911234567890",
            "EMAIL_fraud@example.com",
            "ADDRESS_123_FRAUD_STREET",
            "BANK_ACCT_1234567890"
        }
    
    def analyze_connections(self, claim_data, existing_claims=None):
        """
        Analyze hidden connections for a claim
        
        Args:
            claim_data (dict): Current claim data
            existing_claims (list): Existing claims for network analysis
            
        Returns:
            dict: Connection analysis results
        """
        try:
            # Extract entities from claim data
            entities = self._extract_entities(claim_data)
            
            # Add claim to graph
            self._add_claim_to_graph(claim_data, entities)
            
            # Analyze connections
            connection_analysis = self._analyze_entity_connections(entities)
            
            # Detect communities and clusters
            community_analysis = self._detect_communities()
            
            # Calculate risk score
            risk_score = self._calculate_connection_risk(connection_analysis, community_analysis)
            
            # Compile findings
            findings = self._compile_connection_findings(connection_analysis, community_analysis, risk_score)
            
            return {
                "connection_risk_score": risk_score,
                "entities_found": entities,
                "connection_analysis": connection_analysis,
                "community_analysis": community_analysis,
                "findings": findings,
                "high_risk_connections": risk_score > 70,
                "graph_stats": self._get_graph_statistics()
            }
            
        except Exception as e:
            logger.error(f"Error in connection analysis: {str(e)}")
            return {
                "connection_risk_score": 50,
                "entities_found": {},
                "connection_analysis": {},
                "community_analysis": {},
                "findings": [f"Analysis error: {str(e)}"],
                "high_risk_connections": False,
                "error": str(e)
            }
    
    def _extract_entities(self, claim_data):
        """
        Extract entities from claim data for network analysis
        
        Args:
            claim_data (dict): Claim data
            
        Returns:
            dict: Extracted entities by type
        """
        entities = defaultdict(list)
        
        # Extract from claimant information
        claimant = claim_data.get('claimant', {})
        
        # Phone numbers
        if claimant.get('phone'):
            entities['phone'].append(f"PHONE_{claimant['phone']}")
        
        # Email addresses
        if claimant.get('email'):
            entities['email'].append(f"EMAIL_{claimant['email']}")
        
        # Address components
        if claimant.get('address'):
            address = claimant['address']
            # Extract address components for fuzzy matching
            if address.get('street'):
                entities['address'].append(f"ADDRESS_{address['street']}")
            if address.get('city'):
                entities['location'].append(f"CITY_{address['city']}")
            if address.get('zip_code'):
                entities['location'].append(f"ZIP_{address['zip_code']}")
        
        # Bank account information
        if claimant.get('bank_account'):
            entities['bank_account'].append(f"BANK_ACCT_{claimant['bank_account']}")
        
        # Aadhar number
        if claimant.get('aadhar_number'):
            entities['government_id'].append(f"AADHAR_{claimant['aadhar_number']}")
        
        # Policy information
        if claim_data.get('policy_number'):
            entities['policy'].append(f"POLICY_{claim_data['policy_number']}")
        
        # IP address (from submission)
        if claim_data.get('submission_ip'):
            entities['digital'].append(f"IP_{claim_data['submission_ip']}")
        
        # Device fingerprint
        if claim_data.get('device_id'):
            entities['digital'].append(f"DEVICE_{claim_data['device_id']}")
        
        # Medical providers (if health claim)
        if claim_data.get('medical_provider'):
            entities['provider'].append(f"PROVIDER_{claim_data['medical_provider']}")
        
        # Repair shops (if auto claim)
        if claim_data.get('repair_shop'):
            entities['provider'].append(f"REPAIR_{claim_data['repair_shop']}")
        
        return dict(entities)
    
    def _add_claim_to_graph(self, claim_data, entities):
        """
        Add claim and its entities to the fraud detection graph
        
        Args:
            claim_data (dict): Claim data
            entities (dict): Extracted entities
        """
        claim_id = claim_data.get('claim_id', f"CLAIM_{hashlib.md5(str(claim_data).encode()).hexdigest()[:8]}")
        
        # Add claim node
        self.graph.add_node(claim_id, node_type='claim', **{
            'amount': claim_data.get('claim_amount', 0),
            'claim_type': claim_data.get('claim_type', 'unknown'),
            'date': claim_data.get('submission_date', ''),
            'status': 'new'
        })
        
        # Add entities and create connections
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                # Add entity node if not exists
                if entity not in self.graph:
                    self.graph.add_node(entity, node_type=entity_type.split('_')[0].lower())
                
                # Create connection between claim and entity
                self.graph.add_edge(claim_id, entity, relationship=entity_type)
                
                # Check if entity is known fraudulent
                if entity in self.known_fraudulent_entities:
                    self.graph.nodes[claim_id]['fraud_connection'] = True
                    self.graph.nodes[entity]['known_fraud'] = True
    
    def _analyze_entity_connections(self, entities):
        """
        Analyze connections between entities
        
        Args:
            entities (dict): Extracted entities
            
        Returns:
            dict: Connection analysis results
        """
        analysis = {
            'direct_connections': [],
            'indirect_connections': [],
            'known_fraud_connections': [],
            'connection_strength': 0
        }
        
        all_entities = [entity for entity_list in entities.values() for entity in entity_list]
        
        for entity in all_entities:
            # Check direct connections to known fraudulent entities
            if entity in self.known_fraudulent_entities:
                analysis['known_fraud_connections'].append({
                    'entity': entity,
                    'type': 'direct',
                    'risk': 'high'
                })
            
            # Check connections to other claims through this entity
            if entity in self.graph:
                neighbors = list(self.graph.neighbors(entity))
                claim_neighbors = [n for n in neighbors if self.graph.nodes[n].get('node_type') == 'claim']
                
                if len(claim_neighbors) > 1:
                    analysis['direct_connections'].append({
                        'entity': entity,
                        'connected_claims': len(claim_neighbors),
                        'risk': 'medium' if len(claim_neighbors) > 2 else 'low'
                    })
        
        # Check for indirect connections (2nd degree)
        for i, entity1 in enumerate(all_entities):
            for entity2 in all_entities[i+1:]:
                if entity1 in self.graph and entity2 in self.graph:
                    try:
                        path = nx.shortest_path(self.graph, entity1, entity2)
                        if len(path) > 2:  # Indirect connection
                            analysis['indirect_connections'].append({
                                'entity1': entity1,
                                'entity2': entity2,
                                'path_length': len(path) - 1,
                                'path': path
                            })
                    except nx.NetworkXNoPath:
                        pass
        
        # Calculate connection strength
        analysis['connection_strength'] = self._calculate_connection_strength(analysis)
        
        return analysis
    
    def _calculate_connection_strength(self, analysis):
        """
        Calculate overall connection strength score
        
        Args:
            analysis (dict): Connection analysis results
            
        Returns:
            float: Connection strength score (0-100)
        """
        score = 0
        
        # Known fraud connections (high weight)
        for conn in analysis['known_fraud_connections']:
            score += 30
        
        # Direct connections to multiple claims
        for conn in analysis['direct_connections']:
            if conn['risk'] == 'high':
                score += 25
            elif conn['risk'] == 'medium':
                score += 15
            else:
                score += 5
        
        # Indirect connections (lower weight)
        for conn in analysis['indirect_connections']:
            if conn['path_length'] <= 3:  # Close connections
                score += 10
            else:
                score += 5
        
        return min(100, score)
    
    def _detect_communities(self):
        """
        Detect communities in the fraud graph using Louvain method
        
        Returns:
            dict: Community analysis results
        """
        analysis = {
            'communities_detected': 0,
            'suspicious_communities': [],
            'modularity_score': 0
        }
        
        if len(self.graph.nodes) < 3:
            return analysis
        
        try:
            # Convert to undirected graph for community detection
            undirected_graph = self.graph.to_undirected()
            
            # Detect communities using Louvain method
            partition = community_louvain.best_partition(undirected_graph)
            analysis['modularity_score'] = community_louvain.modularity(partition, undirected_graph)
            analysis['communities_detected'] = len(set(partition.values()))
            
            # Analyze each community
            communities = defaultdict(list)
            for node, community_id in partition.items():
                communities[community_id].append(node)
            
            for community_id, nodes in communities.items():
                community_analysis = self._analyze_community(nodes)
                if community_analysis['suspicious']:
                    analysis['suspicious_communities'].append(community_analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in community detection: {str(e)}")
            return analysis
    
    def _analyze_community(self, nodes):
        """
        Analyze a single community for suspicious patterns
        
        Args:
            nodes (list): Nodes in the community
            
        Returns:
            dict: Community analysis
        """
        analysis = {
            'node_count': len(nodes),
            'claim_count': 0,
            'fraud_connection_count': 0,
            'entity_types': defaultdict(int),
            'suspicious': False
        }
        
        for node in nodes:
            node_data = self.graph.nodes[node]
            node_type = node_data.get('node_type', 'unknown')
            
            analysis['entity_types'][node_type] += 1
            
            if node_type == 'claim':
                analysis['claim_count'] += 1
                if node_data.get('fraud_connection', False):
                    analysis['fraud_connection_count'] += 1
        
        # Mark as suspicious if multiple claims with fraud connections
        if analysis['claim_count'] >= 3 and analysis['fraud_connection_count'] > 0:
            analysis['suspicious'] = True
            analysis['risk_level'] = 'high'
        elif analysis['claim_count'] >= 2:
            analysis['suspicious'] = True
            analysis['risk_level'] = 'medium'
        
        return analysis
    
    def _calculate_connection_risk(self, connection_analysis, community_analysis):
        """
        Calculate overall connection risk score
        
        Args:
            connection_analysis (dict): Connection analysis results
            community_analysis (dict): Community analysis results
            
        Returns:
            float: Connection risk score (0-100)
        """
        risk_score = connection_analysis['connection_strength']
        
        # Add community risk factors
        for community in community_analysis['suspicious_communities']:
            if community['risk_level'] == 'high':
                risk_score += 25
            else:
                risk_score += 15
        
        # Adjust based on modularity (well-defined communities are more suspicious)
        risk_score += community_analysis['modularity_score'] * 20
        
        return min(100, max(0, risk_score))
    
    def _compile_connection_findings(self, connection_analysis, community_analysis, risk_score):
        """
        Compile human-readable findings from connection analysis
        
        Args:
            connection_analysis (dict): Connection analysis results
            community_analysis (dict): Community analysis results
            risk_score (float): Overall risk score
            
        Returns:
            list: Human-readable findings
        """
        findings = []
        
        # Known fraud connections
        for conn in connection_analysis['known_fraud_connections']:
            findings.append(f"Direct connection to known fraudulent entity: {conn['entity']}")
        
        # Direct connections
        for conn in connection_analysis['direct_connections']:
            if conn['risk'] == 'high':
                findings.append(f"Entity {conn['entity']} connected to {conn['connected_claims']} claims (high risk)")
            elif conn['risk'] == 'medium':
                findings.append(f"Entity {conn['entity']} connected to {conn['connected_claims']} claims")
        
        # Community findings
        for community in community_analysis['suspicious_communities']:
            findings.append(
                f"Suspicious community detected: {community['claim_count']} claims with "
                f"{community['fraud_connection_count']} fraud connections"
            )
        
        # Overall assessment
        if risk_score >= 80:
            findings.append("High risk of organized fraud - strong network connections detected")
        elif risk_score >= 60:
            findings.append("Moderate risk of coordinated fraud activity")
        elif risk_score >= 40:
            findings.append("Some network connections detected - monitor for patterns")
        else:
            findings.append("No significant suspicious connections detected")
        
        return findings
    
    def _get_graph_statistics(self):
        """
        Get current graph statistics
        
        Returns:
            dict: Graph statistics
        """
        return {
            'total_nodes': len(self.graph.nodes),
            'total_edges': len(self.graph.edges),
            'claim_nodes': len([n for n, data in self.graph.nodes(data=True) if data.get('node_type') == 'claim']),
            'entity_nodes': len([n for n, data in self.graph.nodes(data=True) if data.get('node_type') != 'claim']),
            'known_fraud_nodes': len([n for n, data in self.graph.nodes(data=True) if data.get('known_fraud', False)]),
            'average_degree': sum(dict(self.graph.degree()).values()) / len(self.graph.nodes) if self.graph.nodes else 0
        }
    
    def find_similar_claims(self, claim_data, max_results=5):
        """
        Find claims with similar patterns
        
        Args:
            claim_data (dict): Claim data to match
            max_results (int): Maximum number of similar claims to return
            
        Returns:
            list: Similar claims with similarity scores
        """
        try:
            entities = self._extract_entities(claim_data)
            all_entities = [entity for entity_list in entities.values() for entity in entity_list]
            
            similar_claims = []
            
            for node, data in self.graph.nodes(data=True):
                if data.get('node_type') == 'claim' and node != claim_data.get('claim_id'):
                    # Calculate similarity based on shared entities
                    claim_entities = set(self.graph.neighbors(node))
                    shared_entities = claim_entities.intersection(all_entities)
                    
                    if shared_entities:
                        similarity = len(shared_entities) / len(set(all_entities).union(claim_entities))
                        similar_claims.append({
                            'claim_id': node,
                            'similarity_score': similarity,
                            'shared_entities': list(shared_entities),
                            'claim_data': data
                        })
            
            # Sort by similarity and return top results
            similar_claims.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_claims[:max_results]
            
        except Exception as e:
            logger.error(f"Error finding similar claims: {str(e)}")
            return []
    
    def save_graph(self):
        """Save the current graph to file"""
        try:
            nx.write_gexf(self.graph, self.graph_path)
            logger.info(f"Graph saved to {self.graph_path}")
        except Exception as e:
            logger.error(f"Error saving graph: {str(e)}")
    
    def load_graph(self):
        """Load graph from file"""
        try:
            if os.path.exists(self.graph_path):
                self.graph = nx.read_gexf(self.graph_path)
                logger.info(f"Graph loaded from {self.graph_path}")
        except Exception as e:
            logger.error(f"Error loading graph: {str(e)}")
    
    def add_known_fraudulent_entities(self, entities):
        """
        Add known fraudulent entities to the database
        
        Args:
            entities (list): List of fraudulent entities to add
        """
        self.known_fraudulent_entities.update(entities)
        # Also update graph nodes
        for entity in entities:
            if entity in self.graph:
                self.graph.nodes[entity]['known_fraud'] = True

# Singleton instance
hidden_link_ai = HiddenLinkAI()
