import unittest
import math
from CrimeVision import haversine_distance, run_kmeans, compute_knn_prediction, load_data, CRIME_DATA

class TestMLComponents(unittest.TestCase):
    
    def setUp(self):
        # Ensure default dataset is loaded
        load_data()
        
    def test_haversine_distance(self):
        # Coordinates of India Gate and Connaught Place in Delhi
        india_gate = (28.6129, 77.2295)
        connaught_place = (28.6304, 77.2177)
        
        dist = haversine_distance(india_gate, connaught_place)
        
        # Expected distance is ~2.21 km
        self.assertAlmostEqual(dist, 2.21, delta=0.2)
        
        # Distance to self should be 0
        self.assertEqual(haversine_distance(india_gate, india_gate), 0.0)

    def test_kmeans_basic(self):
        # Create clear separation of points
        # Cluster A: near Connaught Place
        # Cluster B: near Dwarka
        test_points = [
            {'latitude': 28.630, 'longitude': 77.217, 'category': 'Theft', 'severity': 2},
            {'latitude': 28.631, 'longitude': 77.218, 'category': 'Theft', 'severity': 3},
            {'latitude': 28.629, 'longitude': 77.216, 'category': 'Theft', 'severity': 2},
            
            {'latitude': 28.585, 'longitude': 77.049, 'category': 'Burglary', 'severity': 1},
            {'latitude': 28.586, 'longitude': 77.050, 'category': 'Burglary', 'severity': 2},
            {'latitude': 28.584, 'longitude': 77.048, 'category': 'Burglary', 'severity': 1}
        ]
        
        centroids, clusters = run_kmeans(test_points, k=2, max_iters=20)
        
        self.assertEqual(len(centroids), 2)
        self.assertEqual(len(clusters), 2)
        
        # Each cluster should contain exactly 3 points
        self.assertEqual(len(clusters[0]), 3)
        self.assertEqual(len(clusters[1]), 3)

    def test_kmeans_edge_cases(self):
        # K larger than points count
        test_points = [
            {'latitude': 28.630, 'longitude': 77.217, 'category': 'Theft', 'severity': 2}
        ]
        centroids, clusters = run_kmeans(test_points, k=5)
        self.assertEqual(len(centroids), 1)
        self.assertEqual(len(clusters), 1)
        
        # Empty input points
        centroids, clusters = run_kmeans([], k=3)
        self.assertEqual(centroids, [])
        self.assertEqual(clusters, [])

    def test_knn_prediction(self):
        # Ensure we have data loaded
        self.assertGreater(len(CRIME_DATA), 0)
        
        # Query near Connaught Place hotspot (28.6304, 77.2177)
        # It should show relatively high risk and a valid category
        res = compute_knn_prediction(28.6304, 77.2177, hour=18)
        
        self.assertIn(res['risk_level'], ['Medium', 'High'])
        self.assertGreaterEqual(res['risk_score'], 50)
        self.assertIn(res['predicted_category'], ['Theft', 'Assault', 'Burglary', 'Cyber Crime', 'Harassment'])
        self.assertTrue(len(res['safety_recommendation']) > 0)
        
        # Query far away in the ocean/abroad where there are no crime incidents
        # (e.g. 15.0, 60.0)
        res_far = compute_knn_prediction(15.0, 60.0, hour=12)
        self.assertEqual(res_far['risk_level'], 'Low')
        self.assertLess(res_far['risk_score'], 15)

if __name__ == '__main__':
    unittest.main()
