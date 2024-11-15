import numpy as np
from typing import List, Literal
from swarmauri.vectors.concrete.Vector import Vector
from swarmauri.distances.base.DistanceBase import DistanceBase


class BrayCurtisDistance(DistanceBase):
    """
    Concrete implementation of the IDistanceSimiliarity interface using the Bray-Curtis Distance metric.
    This class now processes Vector instances instead of raw lists.
    """
    type: Literal['BrayCurtisDistance'] = 'BrayCurtisDistance'   

    def distance(self, vector_a: Vector, vector_b: Vector) -> float:
        """
        Computes the Bray-Curtis Distance between two Vector instances.

        Args:
            vector_a (Vector): The first vector in the comparison.
            vector_b (Vector): The second vector in the comparison.

        Returns:
            float: The computed Bray-Curtis Distance between the vectors.

        Raises:
            ValueError: If the input vectors are None or empty.
        """
        if vector_a is None or vector_b is None:
            raise ValueError("Input vectors cannot be None.")
        if not vector_a.value or not vector_b.value:
            raise ValueError("Input vectors cannot be empty.")

        # Extract data from Vector
        data_a = np.array(vector_a.value)
        data_b = np.array(vector_b.value)

        # Checking dimensions match
        if data_a.shape != data_b.shape:
            raise ValueError("Vectors must have the same dimensionality.")

        # Computing Bray-Curtis Distance
        sum_abs_diff = np.sum(np.abs(data_a - data_b))
        sum_both = np.sum(np.abs(data_a) + np.abs(data_b))
        distance = sum_abs_diff / sum_both

        return distance
    
    def similarity(self, vector_a: Vector, vector_b: Vector) -> float:
        """
        Compute similarity using the Bray-Curtis Distance. Since this distance metric isn't
        directly interpretable as a similarity, a transformation is applied to map the distance
        to a similarity score.

        Args:
            vector_a (Vector): The first vector in the comparison.
            vector_b (Vector): The second vector to compare with the first vector.

        Returns:
            float: A similarity score between vector_a and vector_b.

        Raises:
            ValueError: If the input vectors are None or empty.
        """
        if vector_a is None or vector_b is None:
            raise ValueError("Input vectors cannot be None.")
        if not vector_a.value or not vector_b.value:
            raise ValueError("Input vectors cannot be empty.")

        # One way to derive a similarity from distance is through inversion or transformation.
        # Here we use an exponential decay based on the computed distance. This is a placeholder
        # that assumes closer vectors (smaller distance) are more similar.
        distance = self.distance(vector_a, vector_b)

        # Transform the distance into a similarity score
        similarity = np.exp(-distance)

        return similarity
    
    def distances(self, vector_a: Vector, vectors_b: List[Vector]) -> List[float]:
        """
        Computes the distances between the input vector and a list of vectors.

        Args:
            vector_a (Vector): The vector to compare with the list of vectors.
            vectors_b (List[Vector]): The list of vectors to compare with the input vector.

        Returns:
            List[float]: A list of distances between the input vector and each vector in the list.
        """
        return [self.distance(vector_a, vector_b) for vector_b in vectors_b]
    
    def similarities(self, vector_a: Vector, vectors_b: List[Vector]) -> List[float]:
        """
        Computes the similarities between the input vector and a list of vectors using the Bray-Curtis Distance metric.

        Args:
            vector_a (Vector): The vector to compare with the list of vectors.
            vectors_b (List[Vector]): The list of vectors to compare with the input vector.

        Returns:
            List[float]: A list of similarities between the input vector and each vector in the list.
        """
        return [self.similarity(vector_a, vector_b) for vector_b in vectors_b]
