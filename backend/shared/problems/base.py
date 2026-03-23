#abstract base class for problems, to be implemented by all concrete problems

from abc import ABC, abstractmethod
from typing import Any, List


class BaseProblem(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this problem, used to route requests."""

    @abstractmethod
    def split(self, input_data: Any, num_chunks: int) -> List[Any]:
        """
        Partition *input_data* into *num_chunks* independent pieces.

        Parameters
        ----------
        input_data : Any
            The raw problem input (string, list, dict, …).
        num_chunks : int
            Desired number of chunks (≥ 1).  Implementations may return
            fewer chunks if the data is smaller than num_chunks.

        Returns
        -------
        List[Any]
            A list of chunk payloads that will each be sent to one worker.
        """

    @abstractmethod
    def solve(self, chunk: Any) -> Any:
        """
        Process a single chunk and return a partial result.

        Parameters
        ----------
        chunk : Any
            One element from the list returned by split().

        Returns
        -------
        Any
            A JSON-serialisable partial result to be used in agregation
        """

    @abstractmethod
    def aggregate(self, partial_results: List[Any]) -> Any:
        """
        Combine all partial results into the final answer.


        Parameters
        ----------
        partial_results : List[Any]
            Ordered list of return values from solve(), one per chunk.

        Returns
        -------
        Any
            The final, merged answer.
        """
