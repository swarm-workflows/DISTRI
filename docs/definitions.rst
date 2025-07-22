===================
Metric definitions
===================

.. contents::

.. toctree::
   :hidden:


Throughput
==========

Throughput is defined as the amount of data successfully transmitted over the network per unit time. It is a measure of the system's ability to handle data transmission efficiently. The throughput :math:`T` at a time :math:`t` can be calculated as:

.. math::
   \begin{equation}
   T(t) = \frac{D_{a}(t)}{\Delta t}
   \end{equation}

where :math:`D_{a}(t)` is the total amount of data acknowledged during the time interval :math:`\Delta t`.

The average throughput :math:`\bar{T}` over a defined time interval :math:`\Delta t` can be calculated as:

.. math::
   \begin{equation}
   \bar{T} = \frac{1}{N_f} \sum_{i=1}^{N_f} T_i
   \end{equation}

where :math:`N_f` is the number of flows and :math:`T_i` is the throughput of flow :math:`i`.

Goodput
=======

Goodput refers to the amount of useful data transmitted over the network per unit time, excluding retransmitted packets and algorithm overhead. It provides a measure of effective data transfer. The goodput :math:`G` at a time :math:`t` can be calculated as:

.. math::
   \begin{equation}
   G(t) = \frac{D_{g}(t)}{\Delta t}
   \end{equation}

where :math:`D_{g}(t)` is the total amount of useful data acknowledged during the time interval :math:`\Delta t`.

The average goodput :math:`\bar{G}` over a defined time interval :math:`\Delta t` can be calculated as:

.. math::
   \begin{equation}
   \bar{G} = \frac{1}{N_f} \sum_{i=1}^{N_f} G_i
   \end{equation}

where :math:`N_f` is the number of flows and :math:`G_i` is the goodput of flow :math:`i`.

Congestion Window (CWND)
========================

The CWND is a TCP metric that determines the number of packets a sender can transmit without receiving an ACK. It is dynamically adjusted by the CCA based on network conditions to control congestion. The value of the CWND at a time :math:`t` is denoted as :math:`CWND(t)`.

The average CWND :math:`\overline{CWND}` over a defined time interval :math:`\Delta t` can be calculated as:

.. math::
   \begin{equation}
   \overline{CWND} = \frac{1}{N_f} \sum_{i=1}^{N_f} CWND_i
   \end{equation}

where :math:`N_f` is the number of flows and :math:`CWND_i` is the CWND size of flow :math:`i`.

Round-Trip Time (RTT)
=====================


Round-trip time (RTT) is the time taken for a packet to travel from the sender to the receiver and back. It is a critical metric for evaluating network performance. The RTT :math:`RTT(t)` at a time :math:`t` can be calculated as:

.. math::
   \begin{equation}
   RTT(t) = \frac{1}{N_f} \sum_{i=1}^{N_f} RTT_i
   \end{equation}

where :math:`N_f` is the number of flows and :math:`RTT_i` is the RTT for flow :math:`i`.

The average RTT :math:`\overline{RTT}` over a defined time interval :math:`\Delta t` can be calculated as:

.. math::
   \begin{equation}
   \overline{RTT} = \frac{1}{N_f} \sum_{i=1}^{N_f} RTT_i
   \end{equation}

where :math:`N_f` is the number of flows and :math:`RTT_i` is the RTT of flow :math:`i`.


Retransmissions
===============

Retransmissions refer to the number of packets that need to be resent due to loss or errors. It is an indicator of network reliability and congestion. The total number of retransmissions :math:`R` at a time :math:`t` can be summed up as:

.. math::
   \begin{equation}
   R(t) = \sum_{i=1}^{N_f} r_i
   \end{equation}

where :math:`N_f` is the total number of flows and :math:`r_i` is the number of retransmissions for flow :math:`i`.

The average number of retransmissions :math:`\bar{R}` over a defined time interval :math:`\Delta t` can be calculated as:

.. math::
   \begin{equation}
   \bar{R} = \frac{1}{N_f} \sum_{i=1}^{N_f} r_i
   \end{equation}

where :math:`N_f` is the number of flows and :math:`r_i` is the number of retransmissions for flow :math:`i`.

Average Queue Length
====================

Average queue length measures the average number of packets in the queue over a given time period. It is an important metric for understanding congestion at network routers. The average queue length :math:`\bar{Q}` can be calculated as:

.. math::
   \begin{equation}
   \bar{Q} = \frac{1}{\Delta t} \int_{0}^{\Delta t} Q(t) , dt
   \end{equation}

where :math:`Q(t)` is the queue length at time :math:`t`.


Job Failure Count
=================

Job failure count refers to the number of instances a job experiences failures or disruptions during its execution. It is a measure of system reliability. For a job :math:`i`, the job failure count :math:`F_{i}` can be recorded as the number of disruptions the job experiences during its lifetime.

