# spring-projects/spring-petclinic

Commit 500158f. Kind: service. Written by openrouter:nvidia/nemotron-3-ultra-550b-a55b:free.
50 of 50 claims kept after checking them against the code.

## Overview

- This repository is a service with 17 routes, consumers, or scheduled jobs. ([f1](#f1))
- It contains 30 Java source files totaling 1,899 lines, 12 HTML files, 5 CSS files, and 7 SQL files. ([f2](#f2), [f3](#f3), [f4](#f4), [f5](#f5))
- The project supports both Maven and Gradle builds as indicated by the presence of pom.xml and build.gradle. ([f10](#f10), [f12](#f12))
- CI/CD is configured via GitHub Actions workflows for Maven builds, Gradle builds, and cluster deployment, and Docker support includes a Dockerfile and docker-compose.yml. ([f6](#f6), [f7](#f7), [f8](#f8), [f9](#f9), [f11](#f11))

## System design

- The application includes dependencies for three databases: H2, MySQL, and PostgreSQL. ([f13](#f13), [f14](#f14), [f15](#f15))
- Docker Compose defines a MySQL service using image mysql:9.7 and a PostgreSQL service using image postgres:18.4. ([f14](#f14), [f15](#f15))
- MySQL connection settings MYSQL_URL, MYSQL_USER, and MYSQL_PASS are read from the environment in src/main/resources/application-mysql.properties. ([f16](#f16), [f17](#f17), [f18](#f18))
- PostgreSQL connection settings POSTGRES_URL, POSTGRES_USER, and POSTGRES_PASS are read from the environment in src/main/resources/application-postgres.properties. ([f19](#f19), [f20](#f20), [f21](#f21))

## How a request moves

- 15 of 17 traced routes reach the database. ([f42](#f42))
- POST /owners/{ownerId}/pets/{petId}/edit is handled by PetController.processUpdateForm in src/main/java/org/springframework/samples/petclinic/owner/PetController.java. ([f43](#f43))
- The framework first runs PetController.populatePetTypes, PetController.findOwner, and PetController.findPet before the handler. ([f43](#f43))
- PetController.processUpdateForm calls PetController.updatePetDetails and PetController.isDuplicatePetNameViolation. ([f43](#f43))
- PetController.populatePetTypes reaches the database via PetTypeRepository.findPetTypes in PetController.java. ([f43](#f43))
- POST /owners/{ownerId}/pets/new is handled by PetController.processCreationForm in PetController.java. ([f44](#f44))
- The framework first runs PetController.populatePetTypes, PetController.findOwner, and PetController.findPet before the handler. ([f44](#f44))
- PetController.processCreationForm calls Owner.addPet in Owner.java and PetController.isDuplicatePetNameViolation. ([f44](#f44))
- PetController.processCreationForm reaches the database via OwnerRepository.saveAndFlush in PetController.java. ([f44](#f44))
- GET /vets.html is handled by VetController.showVetList in src/main/java/org/springframework/samples/petclinic/vet/VetController.java. ([f45](#f45))
- VetController.showVetList calls VetController.findPaginated and VetController.addPaginationModel. ([f45](#f45))
- VetController.findPaginated reaches the database via VetRepository.findAll in VetController.java. ([f45](#f45))
- GET /vets is handled by VetController.showResourcesVetList in VetController.java. ([f46](#f46))
- VetController.showResourcesVetList calls Vets.getVetList in Vets.java. ([f46](#f46))
- VetController.showResourcesVetList reaches the database via VetRepository.findAll in VetController.java. ([f46](#f46))

## Ways into the code

- The application starts from the PetClinicApplication class in src/main/java/org/springframework/samples/petclinic/PetClinicApplication.java. ([f40](#f40), [f41](#f41))
- There are 17 HTTP routes defined across six controllers. ([f22](#f22))
- OwnerController handles seven routes for owner management including listing, finding, creating, viewing, and editing owners. ([f23](#f23), [f24](#f24), [f25](#f25), [f26](#f26), [f27](#f27), [f28](#f28), [f29](#f29))
- PetController provides four routes for creating and editing pets under specific owners. ([f30](#f30), [f31](#f31), [f32](#f32), [f33](#f33))
- VisitController exposes two routes for creating visits for specific pets. ([f34](#f34), [f35](#f35))
- VetController serves two routes for viewing veterinarians at /vets and /vets.html. ([f38](#f38), [f39](#f39))
- WelcomeController maps the root path /. ([f37](#f37))
- CrashController provides a single route at /oups. ([f36](#f36))

## Code map

- The codebase has 30 Java source files totaling 1,899 lines, 5 CSS files with 9,920 lines, 12 HTML files with 546 lines, and 7 SQL files with 344 lines. ([f2](#f2), [f3](#f3), [f4](#f4), [f5](#f5))
- The owner package (src/main/java/org/springframework/samples/petclinic/owner) uses the model package with 4 references. ([f52](#f52))
- The vet package (src/main/java/org/springframework/samples/petclinic/vet) uses the model package with 3 references. ([f53](#f53))
- The root petclinic package uses the model package with 2 references. ([f54](#f54))
- The root petclinic package uses the vet package with 1 reference. ([f55](#f55))
- Test code in the owner test package references the main owner package 25 times. ([f56](#f56))
- Test code in the service test package references the main owner package 6 times. ([f57](#f57))
- Owner.java is used by 10 other files. ([f58](#f58))
- Pet.java is used by 10 other files. ([f59](#f59))
- PetType.java is used by 9 other files. ([f60](#f60))
- OwnerRepository.java is used by 8 other files. ([f61](#f61))
- Vet.java is used by 7 other files. ([f62](#f62))

## Hot spots

- There were 13 commits between 01 Jul 2026 and 29 Sep 2026. ([f63](#f63))
- src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java changed in 3 commits by 2 authors during that period. ([f65](#f65))
- src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java changed in 3 commits by 3 authors during that period. ([f64](#f64))

## How to contribute

- CI runs ./gradlew build in the gradle-build.yml workflow. ([f50](#f50))
- CI runs ./mvnw -B verify in the maven-build.yml workflow. ([f51](#f51))
- CI deploys to a cluster with kubectl apply -f k8s/ in the deploy-and-test-cluster.yml workflow. ([f47](#f47))
- CI waits for demo-db and petclinic pods to become ready with kubectl wait commands. ([f48](#f48), [f49](#f49))

## Sources

- <a id="f1"></a>**f1**: Looks like a service repo: 17 route(s), consumer(s) or scheduled job(s). `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 72; `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 77; `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 89
- <a id="f2"></a>**f2**: 5 source files in css, 9,920 lines in all. `src/main/resources/static/resources/css/petclinic.css`; `src/main/scss/petclinic.scss`; `src/main/scss/header.scss`
- <a id="f3"></a>**f3**: 30 source files in java, 1,899 lines in all. `src/main/java/org/springframework/samples/petclinic/owner/PetController.java`; `src/main/java/org/springframework/samples/petclinic/owner/Owner.java`; `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java`
- <a id="f4"></a>**f4**: 12 source files in html, 546 lines in all. `src/main/resources/templates/owners/ownerDetails.html`; `src/main/resources/templates/fragments/layout.html`; `src/main/resources/templates/owners/ownersList.html`
- <a id="f5"></a>**f5**: 7 source files in sql, 344 lines in all. `src/main/resources/db/h2/schema.sql`; `src/main/resources/db/mysql/schema.sql`; `src/main/resources/db/h2/data.sql`
- <a id="f6"></a>**f6**: Build or deploy file .devcontainer/Dockerfile. `.devcontainer/Dockerfile`
- <a id="f7"></a>**f7**: GitHub Actions workflow .github/workflows/deploy-and-test-cluster.yml. `.github/workflows/deploy-and-test-cluster.yml`
- <a id="f8"></a>**f8**: GitHub Actions workflow .github/workflows/gradle-build.yml. `.github/workflows/gradle-build.yml`
- <a id="f9"></a>**f9**: GitHub Actions workflow .github/workflows/maven-build.yml. `.github/workflows/maven-build.yml`
- <a id="f10"></a>**f10**: Build or deploy file build.gradle. `build.gradle`
- <a id="f11"></a>**f11**: Build or deploy file docker-compose.yml. `docker-compose.yml`
- <a id="f12"></a>**f12**: Build or deploy file pom.xml. `pom.xml`
- <a id="f13"></a>**f13**: Database, cache or queue: H2 (dependency com.h2database:h2). `build.gradle` line 46; `pom.xml` line 78
- <a id="f14"></a>**f14**: Database, cache or queue: MySQL (dependency com.mysql:mysql-connector-j; setting mentions jdbc:mysql:; Compose service mysql, image mysql:9.7). `build.gradle` line 47; `pom.xml` line 88; `src/main/resources/application-mysql.properties` line 3; `docker-compose.yml` line 2
- <a id="f15"></a>**f15**: Database, cache or queue: PostgreSQL (dependency org.postgresql:postgresql; setting mentions jdbc:postgresql:; Compose service postgres, image postgres:18.4). `build.gradle` line 48; `pom.xml` line 93; `src/main/resources/application-postgres.properties` line 3; `docker-compose.yml` line 14
- <a id="f16"></a>**f16**: Setting MYSQL_PASS is read from the environment in src/main/resources/application-mysql.properties. `src/main/resources/application-mysql.properties` line 5
- <a id="f17"></a>**f17**: Setting MYSQL_URL is read from the environment in src/main/resources/application-mysql.properties. `src/main/resources/application-mysql.properties` line 3
- <a id="f18"></a>**f18**: Setting MYSQL_USER is read from the environment in src/main/resources/application-mysql.properties. `src/main/resources/application-mysql.properties` line 4
- <a id="f19"></a>**f19**: Setting POSTGRES_PASS is read from the environment in src/main/resources/application-postgres.properties. `src/main/resources/application-postgres.properties` line 5
- <a id="f20"></a>**f20**: Setting POSTGRES_URL is read from the environment in src/main/resources/application-postgres.properties. `src/main/resources/application-postgres.properties` line 3
- <a id="f21"></a>**f21**: Setting POSTGRES_USER is read from the environment in src/main/resources/application-postgres.properties. `src/main/resources/application-postgres.properties` line 4
- <a id="f22"></a>**f22**: 17 http routes found. `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 72; `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 77; `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 89
- <a id="f23"></a>**f23**: HTTP route GET /owners/new (spring) in src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java. `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 72
- <a id="f24"></a>**f24**: HTTP route POST /owners/new (spring) in src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java. `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 77
- <a id="f25"></a>**f25**: HTTP route GET /owners/find (spring) in src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java. `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 89
- <a id="f26"></a>**f26**: HTTP route GET /owners (spring) in src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java. `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 94
- <a id="f27"></a>**f27**: HTTP route GET /owners/{ownerId}/edit (spring) in src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java. `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 148
- <a id="f28"></a>**f28**: HTTP route POST /owners/{ownerId}/edit (spring) in src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java. `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 153
- <a id="f29"></a>**f29**: HTTP route GET /owners/{ownerId} (spring) in src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java. `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 178
- <a id="f30"></a>**f30**: HTTP route GET /owners/{ownerId}/pets/new (spring) in src/main/java/org/springframework/samples/petclinic/owner/PetController.java. `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 100
- <a id="f31"></a>**f31**: HTTP route POST /owners/{ownerId}/pets/new (spring) in src/main/java/org/springframework/samples/petclinic/owner/PetController.java. `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 107
- <a id="f32"></a>**f32**: HTTP route GET /owners/{ownerId}/pets/{petId}/edit (spring) in src/main/java/org/springframework/samples/petclinic/owner/PetController.java. `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 139
- <a id="f33"></a>**f33**: HTTP route POST /owners/{ownerId}/pets/{petId}/edit (spring) in src/main/java/org/springframework/samples/petclinic/owner/PetController.java. `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 144
- <a id="f34"></a>**f34**: HTTP route GET /owners/{ownerId}/pets/{petId}/visits/new (spring) in src/main/java/org/springframework/samples/petclinic/owner/VisitController.java. `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` line 90
- <a id="f35"></a>**f35**: HTTP route POST /owners/{ownerId}/pets/{petId}/visits/new (spring) in src/main/java/org/springframework/samples/petclinic/owner/VisitController.java. `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` line 97
- <a id="f36"></a>**f36**: HTTP route GET /oups (spring) in src/main/java/org/springframework/samples/petclinic/system/CrashController.java. `src/main/java/org/springframework/samples/petclinic/system/CrashController.java` line 31
- <a id="f37"></a>**f37**: HTTP route GET / (spring) in src/main/java/org/springframework/samples/petclinic/system/WelcomeController.java. `src/main/java/org/springframework/samples/petclinic/system/WelcomeController.java` line 25
- <a id="f38"></a>**f38**: HTTP route GET /vets.html (spring) in src/main/java/org/springframework/samples/petclinic/vet/VetController.java. `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` line 45
- <a id="f39"></a>**f39**: HTTP route GET /vets (spring) in src/main/java/org/springframework/samples/petclinic/vet/VetController.java. `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` line 72
- <a id="f40"></a>**f40**: 1 program entry found. `src/main/java/org/springframework/samples/petclinic/PetClinicApplication.java` line 32
- <a id="f41"></a>**f41**: Program entry PetClinicApplication in src/main/java/org/springframework/samples/petclinic/PetClinicApplication.java. `src/main/java/org/springframework/samples/petclinic/PetClinicApplication.java` line 32
- <a id="f42"></a>**f42**: 15 of 17 traced routes reach the database. `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 67
- <a id="f43"></a>**f43**: POST /owners/{ownerId}/pets/{petId}/edit is handled by PetController.processUpdateForm in src/main/java/org/springframework/samples/petclinic/owner/PetController.java; the framework first runs PetController.populatePetTypes, PetController.findOwner and PetController.findPet; PetController.processUpdateForm calls PetController.updatePetDetails and PetController.isDuplicatePetNameViolation; 1 more step not shown; PetController.populatePetTypes reaches the database (PetTypeRepository.findPetTypes in src/main/java/org/springframework/samples/petclinic/owner/PetController.java). `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 144; `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 62; `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 67; `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 75; `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 186; `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 64
- <a id="f44"></a>**f44**: POST /owners/{ownerId}/pets/new is handled by PetController.processCreationForm in src/main/java/org/springframework/samples/petclinic/owner/PetController.java; the framework first runs PetController.populatePetTypes, PetController.findOwner and PetController.findPet; PetController.processCreationForm calls Owner.addPet in src/main/java/org/springframework/samples/petclinic/owner/Owner.java and PetController.isDuplicatePetNameViolation; PetController.processCreationForm reaches the database (OwnerRepository.saveAndFlush in src/main/java/org/springframework/samples/petclinic/owner/PetController.java). `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 107; `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 62; `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 67; `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 75; `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` line 100; `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 126
- <a id="f45"></a>**f45**: GET /vets.html is handled by VetController.showVetList in src/main/java/org/springframework/samples/petclinic/vet/VetController.java; VetController.showVetList calls VetController.findPaginated and VetController.addPaginationModel; VetController.findPaginated reaches the database (VetRepository.findAll in src/main/java/org/springframework/samples/petclinic/vet/VetController.java). `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` line 45; `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` line 65; `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` line 56; `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` line 69
- <a id="f46"></a>**f46**: GET /vets is handled by VetController.showResourcesVetList in src/main/java/org/springframework/samples/petclinic/vet/VetController.java; VetController.showResourcesVetList calls Vets.getVetList in src/main/java/org/springframework/samples/petclinic/vet/Vets.java; VetController.showResourcesVetList reaches the database (VetRepository.findAll in src/main/java/org/springframework/samples/petclinic/vet/VetController.java). `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` line 72; `src/main/java/org/springframework/samples/petclinic/vet/Vets.java` line 35; `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` line 77
- <a id="f47"></a>**f47**: CI step "Deploy application" in job deploy-and-test-cluster of .github/workflows/deploy-and-test-cluster.yml runs: kubectl apply -f k8s/. `.github/workflows/deploy-and-test-cluster.yml` line 25
- <a id="f48"></a>**f48**: CI step "Wait for Pods to be ready" in job deploy-and-test-cluster of .github/workflows/deploy-and-test-cluster.yml runs: kubectl wait --for=condition=ready pod -l app=demo-db --timeout=180s. `.github/workflows/deploy-and-test-cluster.yml` line 29
- <a id="f49"></a>**f49**: CI step "Wait for Pods to be ready" in job deploy-and-test-cluster of .github/workflows/deploy-and-test-cluster.yml runs: kubectl wait --for=condition=ready pod -l app=petclinic --timeout=180s. `.github/workflows/deploy-and-test-cluster.yml` line 30
- <a id="f50"></a>**f50**: CI step "Build with Gradle" in job build of .github/workflows/gradle-build.yml runs: ./gradlew build. `.github/workflows/gradle-build.yml` line 31
- <a id="f51"></a>**f51**: CI step "Build with Maven Wrapper" in job build of .github/workflows/maven-build.yml runs: ./mvnw -B verify. `.github/workflows/maven-build.yml` line 29
- <a id="f52"></a>**f52**: Code in src/main/java/org/springframework/samples/petclinic/owner uses code in src/main/java/org/springframework/samples/petclinic/model (4 references). `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` line 23; `src/main/java/org/springframework/samples/petclinic/owner/Pet.java` line 24; `src/main/java/org/springframework/samples/petclinic/owner/PetType.java` line 18
- <a id="f53"></a>**f53**: Code in src/main/java/org/springframework/samples/petclinic/vet uses code in src/main/java/org/springframework/samples/petclinic/model (3 references). `src/main/java/org/springframework/samples/petclinic/vet/Specialty.java` line 18; `src/main/java/org/springframework/samples/petclinic/vet/Vet.java` line 24; `src/main/java/org/springframework/samples/petclinic/vet/Vet.java` line 25
- <a id="f54"></a>**f54**: Code in src/main/java/org/springframework/samples/petclinic uses code in src/main/java/org/springframework/samples/petclinic/model (2 references). `src/main/java/org/springframework/samples/petclinic/PetClinicRuntimeHints.java` line 21; `src/main/java/org/springframework/samples/petclinic/PetClinicRuntimeHints.java` line 22
- <a id="f55"></a>**f55**: Code in src/main/java/org/springframework/samples/petclinic uses code in src/main/java/org/springframework/samples/petclinic/vet (1 reference). `src/main/java/org/springframework/samples/petclinic/PetClinicRuntimeHints.java` line 23
- <a id="f56"></a>**f56**: Code in src/test/java/org/springframework/samples/petclinic/owner uses code in src/main/java/org/springframework/samples/petclinic/owner (25 references). `src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java` line 60; `src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java` line 71; `src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java` line 73
- <a id="f57"></a>**f57**: Code in src/test/java/org/springframework/samples/petclinic/service uses code in src/main/java/org/springframework/samples/petclinic/owner (6 references). `src/test/java/org/springframework/samples/petclinic/service/ClinicServiceTests.java` line 34; `src/test/java/org/springframework/samples/petclinic/service/ClinicServiceTests.java` line 35; `src/test/java/org/springframework/samples/petclinic/service/ClinicServiceTests.java` line 36
- <a id="f58"></a>**f58**: src/main/java/org/springframework/samples/petclinic/owner/Owner.java is used by 10 other files. `src/main/java/org/springframework/samples/petclinic/owner/Owner.java`; `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 65; `src/main/java/org/springframework/samples/petclinic/owner/OwnerRepository.java` line 36
- <a id="f59"></a>**f59**: src/main/java/org/springframework/samples/petclinic/owner/Pet.java is used by 10 other files. `src/main/java/org/springframework/samples/petclinic/owner/Pet.java`; `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` line 70; `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 76
- <a id="f60"></a>**f60**: src/main/java/org/springframework/samples/petclinic/owner/PetType.java is used by 9 other files. `src/main/java/org/springframework/samples/petclinic/owner/PetType.java`; `src/main/java/org/springframework/samples/petclinic/owner/Pet.java` line 54; `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 63
- <a id="f61"></a>**f61**: src/main/java/org/springframework/samples/petclinic/owner/OwnerRepository.java is used by 8 other files. `src/main/java/org/springframework/samples/petclinic/owner/OwnerRepository.java`; `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` line 53; `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` line 53
- <a id="f62"></a>**f62**: src/main/java/org/springframework/samples/petclinic/vet/Vet.java is used by 7 other files. `src/main/java/org/springframework/samples/petclinic/vet/Vet.java`; `src/main/java/org/springframework/samples/petclinic/PetClinicRuntimeHints.java` line 23; `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` line 48
- <a id="f63"></a>**f63**: 13 commits between 01 Jul 2026 and 29 Sep 2026. commit 500158f; commit 0d064b0; commit b33136f
- <a id="f64"></a>**f64**: src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java changed in 3 commits by 3 authors between 01 Jul 2026 and 29 Sep 2026. `src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java`; commit 500158f; commit 3c7ab98; commit bb37aad
- <a id="f65"></a>**f65**: src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java changed in 3 commits by 2 authors between 01 Jul 2026 and 29 Sep 2026. `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java`; commit 500158f; commit 0d064b0; commit bb37aad
