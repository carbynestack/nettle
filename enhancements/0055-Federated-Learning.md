# CSEP-0055: Privacy-Preserving Federated Learning

<!-- markdownlint-disable MD051 -->

<!-- TOC -->

- [CSEP-0055: Privacy-Preserving Federated Learning](#csep-0055--privacy-preserving-federated-learning)
  - [Summary](#summary)
    - [Namesake](#namesake)
  - [Motivation](#motivation)
    - [Goals](#goals)
    - [Non-Goals](#non-goals)
  - [Proposal](#proposal)
    - [User Stories](#user-stories)
      - [Story 1](#story-1)
      - [Story 2](#story-2)
    - [Notes/Constraints/Caveats](#notesconstraintscaveats)
    - [Risks and Mitigations](#risks-and-mitigations)
  - [Design Details](#design-details)
    - [Roles](#roles)
    - [Security Model](#security-model)
    - [Data Privacy](#data-privacy)
    - [Aggregation Method](#aggregation-method)
    - [Weight Representation](#weight-representation)
    - [Flow](#flow)
    - [Open Questions](#open-questions)
      - [Data Conversion](#data-conversion)
    - [Missing pieces](#missing-pieces)
  - [Alternatives](#alternatives)
    - [No Global Model Obliviousness](#no-global-model-obliviousness)
    - [Client-side model protection](#client-side-model-protection)
      - [Implementation Ideas](#implementation-ideas)
  - [Infrastructure Needed](#infrastructure-needed)

<!-- TOC -->

<!-- markdownlint-enable MD051 -->

## Summary

Nettle is an integration layer between the [Flower] federated learning framework
and Carbyne Stack. Nettle allows for large-scale privacy-preserving federated
learning with MPC-based secure aggregation and protects against inference
attacks.

### Namesake

A _nettle_ is a chiefly coarse herb armed with stinging hairs. Carbyne Stack
Nettle is a fortified version of Flower that can resist certain kinds of
attacks.

## Motivation

Federated Learning is taking up momentum in many use case areas. In addition, FL
lends itself very well to adding privacy via MPC as the required operations for
secure aggregation and model updates are comparatively lightweight. FL is also a
major technique used in the [CRYPTECS] PfP that adopted Carbyne Stack for
executing MPC workloads.

### Goals

- Provide a service that supports privacy-preserving FL by offloading model
  aggregation and update to a Carbyne Stack Virtual Cloud

### Non-Goals

- Carbyne Stack Python clients
- MPC-based _centralized_ evaluation of the current model

## Proposal

This CSEP describes how a service that supports privacy-preserving FL by
offloading model aggregation and update to a Carbyne Stack Virtual Cloud can be
implemented by integrating Carbyne Stack with the FL framework [Flower]. The
proposal covers a basic scheme that protects data samples and the model from the
central orchestrator. Variations of the basic scheme are also presented: one
with a weaker security model that exposes the global model to the orchestrator
and one with a stronger one that protects the model on the clients as well by
using Confidential Computing techniques.

### User Stories

> **Note** Work in Progress

This is an _optional_ section.

#### Story 1

#### Story 2

### Notes/Constraints/Caveats

> **Note** Work in Progress

This is an _optional_ section.

### Risks and Mitigations

> **Note** Work in Progress

## Design Details

### Roles

- The **Model Owner** is the owner of the global model and the only party in the
  system with clear-text access to it (assuming
  [client-side model protection](#client-side-model-protection) is implemented).

- **Clients** are participants in the FL system that hold local data samples
  that are not shared with other system participants.

- The **Orchestrator** drives the distributed FL process by triggering actions
  on the clients. Coordination includes selection of clients that participate in
  a training round, providing references to the initial and updated model used,
  and evaluating the progress made in a training round. The orchestrator
  delegates updating the model to the aggregator.

- The **Aggregator** receives the model updates from the clients, computes the
  aggregated model update, and updates the global model accordingly. By
  leveraging MPC, the aggregator is oblivious of the updates and the global
  model.

### Security Model

Attacks against FL systems fall into four major categories (see
[this paper][secfl]) for a good overview: poisoning attacks, inference attacks,
communication attacks, and free-riding attacks. The first iteration of Nettle as
described in this CSEP focuses primarily on inference attacks. These attacks try
to extract meaningful insights about the training data via analysis of the
locally derived model updates. Nettle prevents this kind of attacks by hiding
the locally computed model updates from the orchestrator by delegating the
aggregation of updates to an MPC-powered distributed aggregator. Future
iterations may also address other attack classes.

### Data Privacy

The following table summarizes which party is aware of what data in the Nettle
system:

| Knows             | Client                                                         | Orchestrator | Aggregator |
| ----------------- | -------------------------------------------------------------- | ------------ | ---------- |
| **Data Samples**  | Yes                                                            | No           | No         |
| **Model Updates** | Yes / No (if using CC for client-side global model protection) | No           | No         |
| **Global Model**  | Yes / No (if using CC for client-side global model protection) | No           | No         |

### Aggregation Method

Nettle uses the simple aggregation method of [SAFELearn]. SAFELearn uses a
simple calculation of the sum of the model weight updates (local operation in
MPC) followed by a division by the number of sampled clients.

### Weight Representation

The model weights can either be represented by the MP-SPDZ `sfloat` or `sfix`
[data types][mp-spdz-data-types]. While the former results in larger overheads,
the latter leads to quantization errors and potentially degraded accuracy. For
reasons of simplicity this first iteration of Nettle uses weights represented as
`sfix` values. Conversion between the original and quantized weights
representation is done by the clients.

### Flow

The basic Nettle FL flow is described below. In the following with reference
methods of the Flower [NumPyClient][flower-client] and
[Strategy][flower-strategy] classes.

1. The model owner uploads the initial global model to Amphora. For that purpose
   the model is converted into an array of `sfix` values. The
   `initialize_parameters` strategy callback is a no-op.

1. The orchestrator selects clients to participate in the upcoming training
   round in the `configure_fit` strategy callback and sends the global model
   parameters to the selected parties. This is done by transmitting a reference
   to the Amphora secret containing the parameters but does _not_ include the
   model parameters themselves. The reference is stored and transferred in the
   dictionary that is part of the [`FitIns`][flower-fitins] data structure.

1. The clients receive the parameters in the Flower `set_parameters` callback.
   They fetch the model from Amphora using the reference transmitted in step 2.
   The values are translated from the MP-SPDZ `sfix` representation into the
   representation required by Flower (see [here](#data-conversion) for more
   details).

1. The clients perform the training in the [`fit`][flower-fit] callback. After
   local training has been concluded, the model parameters are translated into
   the MP-SPDZ `sfix` representation and stored in Amphora. The reference to the
   Amphora secret is sent to the server as part of the `metrics` dictionary
   returned by the [`fit`][flower-fit] callback.

1. The orchestrator receives the results, i.e., references to the secrets stored
   in Amphora, from the clients in the `aggregate_fit` method of the strategy.
   It triggers the Ephemeral execution that performs the secure aggregation and
   global model update. The Amphora secret identifiers are used as inputs.

1. Flower supports the evaluation of the current model parameters by the
   orchestrator in the `evaluate` strategy callback. In our setting the
   coordinator doesn't know the model and hence is not able to perform the
   evaluation. The `evaluate` method is a no-op. In future versions of Nettle
   the evaluation could be delegated to the Virtual Cloud to be performed using
   MPC.

1. The client-side evaluate phase implemented in the `configure_evaluate` and
   `aggregate_evaluate` strategy callbacks is mostly unaffected by the fact that
   Nettle outsources the aggregation and model update to an MPC-based
   aggregator. The [`EvaluateIns`][flower-evaluateins] data structure produced
   by `configure_evaluate` contains a dummy `Parameters` object only. The
   reference to the Amphora secret containing the updated model parameters from
   Step 5 can be stored in the `config` dictionary and is used on the client to
   reconstruct the clear-text model.

1. Go to step 2 or quit in case the configured number of training rounds have
   been conducted.

### Open Questions

The aspects discussed in the following sections still have to be investigated.

#### Data Conversion

In the flow described above, data has to be converted between NumPy NdArrays and
MP-SPDZ `sfix` values. This will probably be ML framework specific. We might go
for PyTorch first. In that case the datatype stored in NdArrays is probably
`torch.float32`.

### Missing pieces

- Flower is written in Python. As of today, Carbyne Stack has no Python Amphora
  and Ephemeral Clients. A potential (hacky) fallback is to use the CS CLI
  launched via the Python `subprocess` module.

## Alternatives

### No Global Model Obliviousness

In a variation of the above scheme, the system could be built in a way such that
the orchestrator has access to the model parameters. In that case only the
aggregation of the model updates is done using MPC by the aggregator. The model
update is done by orchestrator and the exchange of model parameters with the
clients is done in-band, i.e., via the regular Flower communication channels.

### Client-side model protection

In settings where the model is of high value or otherwise sensitive, the model
must be protected on the client-side as well. While in theory the whole training
could be delegated to an MPC system as well, such an approach would have severe
disadvantages: First, the benefits of data locality in FL schemes would be
voided, as all data would have to be transmitted to the MPC system for
processing. Second, the performance and cost of doing full NN training in MPC is
still very high. Hence, Nettle doesn't implement such an approach.

Instead, Nettle uses Confidential Computing techniques to protect the model on
the clients in this variation.

That implies the following changes to the original system / flow described
[above](#flow):

1. The Nettle/Flower client is executed on top of the [Gramine] library OS.
1. Nettle performs remote attestation before admitting a client to the FL system
   which makes the client eligible for being selected in the `configure_fit` and
   `configure_evaluate` strategy callbacks.

The details of how Step 2 is implemented still have to be worked out.

In case client-side model protection is used with the variation that does expose
the model to the orchestrator (see [above](#no-global-model-obliviousness))
[Gramine Secret Provisioning][gramine-secret-prov] can be used to attest the
clients and inject a secret decryption key. That key is used to decrypt the
model parameters that are transferred in encrypted form by the orchestrator.

#### Implementation Ideas

The model owner is responsible for admitting clients to the system. The
rationale for this as opposed to having this done by the orchestrator is that
the model owner should be able to decide under which circumstances his model is
deployed on a remote system. The admission flow is as follows:

1. The model owner starts the Gramine
   [secret provisioning][gramine-secret-provisioning] service which exposes an
   endpoint that can be used by clients to get attested and to receive a secret
   generated by the model owner.
1. The client uses Gramine secret provisioning via secret injection prior to
   application launch. The details how to achieve this are described
   [here][gramine-secret-injection]. The credentials are provided via the
   `SECRET_PROVISION_SECRET_STRING` environment variable that is transparently
   initialized by Gramine after successful remote attestation. In case remote
   attestation fails the secret is not injected and the client does not start.
   If someone starts a non-protected Flower client, the client still can connect
   to the Flower server but will never be selected for participating in a
   training round. This is ensured as follows:
   1. Successfully remote attested clients provide the received secret to the
      orchestrator in the [`get_properties`][flower-get-properties] method of
      the Flower `NumPyClient`.
   1. The orchestrator uses a special [`Criterion`][flower-criterion] that
      rejects any client that has not provided the correct secret. To check
      that, the criterion implementation has access to a
      [`ClientProxy`][flower-client-proxy] for each connected client. These
      proxies can be used to query the properties provided by the client in the
      previous step.
1. The client launches the Flower client that contacts the Flower server to join
   the FL system.

## Infrastructure Needed

- Repository for hosting the Nettle codebase

[cryptecs]: https://www.cryptecs.eu/
[flower]: https://flower.dev/
[flower-client]: https://flower.dev/docs/tutorial/Flower-4-Client-and-NumPyClient-PyTorch.html#Step-1:-Revisiting-NumPyClient
[flower-client-proxy]: https://github.com/adap/flower/blob/4b15af51da4aa766e18866561882c6d3473aed8c/src/py/flwr/server/client_proxy.py
[flower-criterion]: https://github.com/adap/flower/blob/4b15af51da4aa766e18866561882c6d3473aed8c/src/py/flwr/server/criterion.py
[flower-evaluateins]: https://github.com/adap/flower/blob/2ae0a533c0dabce60402ef6f7d8a4de23e3407e9/src/py/flwr/common/typing.py#L100
[flower-fit]: https://github.com/adap/flower/blob/2ae0a533c0dabce60402ef6f7d8a4de23e3407e9/src/py/flwr/client/numpy_client.py#L61
[flower-fitins]: https://github.com/adap/flower/blob/2ae0a533c0dabce60402ef6f7d8a4de23e3407e9/src/py/flwr/common/typing.py#L82
[flower-get-properties]: https://github.com/adap/flower/blob/4b15af51da4aa766e18866561882c6d3473aed8c/src/py/flwr/client/numpy_client.py#L27
[flower-strategy]: https://flower.dev/docs/implementing-strategies.html#implementing-strategies
[gramine]: https://gramineproject.io/
[gramine-secret-injection]: https://gramine.readthedocs.io/en/stable/tutorials/pytorch/index.html#end-to-end-confidential-pytorch-workflow
[gramine-secret-prov]: https://gramine.readthedocs.io/en/latest/attestation.html#high-level-secret-provisioning-interface
[gramine-secret-provisioning]: https://gramine.readthedocs.io/en/stable/attestation.html#high-level-secret-provisioning-interface
[mp-spdz-data-types]: https://mp-spdz.readthedocs.io/en/latest/Compiler.html#basic-types
[safelearn]: https://eprint.iacr.org/2021/386
[secfl]: https://hal.archives-ouvertes.fr/hal-03620400/document
