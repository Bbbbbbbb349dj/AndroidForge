package com.lagradost.cloudstream3.syncproviders

import android.net.Uri
import androidx.annotation.WorkerThread
import com.fasterxml.jackson.annotation.JsonAlias
import com.fasterxml.jackson.annotation.JsonProperty
import com.lagradost.cloudstream3.ActorData
import com.lagradost.cloudstream3.CloudStreamApp
import com.lagradost.cloudstream3.CloudStreamApp.Companion.getKey
import com.lagradost.cloudstream3.CloudStreamApp.Companion.setKey
import com.lagradost.cloudstream3.CommonActivity.showToast
import com.lagradost.cloudstream3.ErrorLoadingException
import com.lagradost.cloudstream3.LoadResponse
import com.lagradost.cloudstream3.NextAiring
import com.lagradost.cloudstream3.Score
import com.lagradost.cloudstream3.SearchQuality
import com.lagradost.cloudstream3.SearchResponse
import com.lagradost.cloudstream3.ShowStatus
import com.lagradost.cloudstream3.TvType
import com.lagradost.cloudstream3.base64Encode
import com.lagradost.cloudstream3.mvvm.safe
import com.lagradost.cloudstream3.subtitles.AbstractSubtitleEntities.SubtitleEntity
import com.lagradost.cloudstream3.subtitles.AbstractSubtitleEntities.SubtitleSearch
import com.lagradost.cloudstream3.subtitles.SubtitleResource
import com.lagradost.cloudstream3.syncproviders.providers.Addic7ed
import com.lagradost.cloudstream3.syncproviders.providers.AniListApi
import com.lagradost.cloudstream3.syncproviders.providers.KitsuApi
import com.lagradost.cloudstream3.syncproviders.providers.LocalList
import com.lagradost.cloudstream3.syncproviders.providers.MALApi
import com.lagradost.cloudstream3.syncproviders.providers.OpenSubtitlesApi
import com.lagradost.cloudstream3.syncproviders.providers.SimklApi
import com.lagradost.cloudstream3.syncproviders.providers.SubDlApi
import com.lagradost.cloudstream3.syncproviders.providers.SubSourceApi
import com.lagradost.cloudstream3.ui.SyncWatchType
import com.lagradost.cloudstream3.ui.library.ListSorting
import com.lagradost.cloudstream3.utils.DataStoreHelper
import com.lagradost.cloudstream3.utils.UiText
import java.security.SecureRandom
import java.util.Date
import java.util.concurrent.TimeUnit
import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonNames

data class AuthLoginPage(
    val url: String,
    val payload: String? = null,
)

@Serializable
data class AuthToken(
    @JsonProperty("accessToken") @SerialName("accessToken")
    val accessToken: String? = null,
    @JsonProperty("refreshToken") @SerialName("refreshToken")
    val refreshToken: String? = null,
    @JsonProperty("accessTokenLifetime") @SerialName("accessTokenLifetime")
    val accessTokenLifetime: Long? = null,
    @JsonProperty("refreshTokenLifetime") @SerialName("refreshTokenLifetime")
    val refreshTokenLifetime: Long? = null,
    @JsonProperty("payload") @SerialName("payload")
    val payload: String? = null,
) {
    fun isAccessTokenExpired(marginSec: Long = 10L): Boolean =
        accessTokenLifetime != null && (System.currentTimeMillis() / 1000L) + marginSec >= accessTokenLifetime

    fun isRefreshTokenExpired(marginSec: Long = 10L): Boolean =
        refreshTokenLifetime != null && (System.currentTimeMillis() / 1000L) + marginSec >= refreshTokenLifetime
}

@OptIn(ExperimentalSerializationApi::class)
@Serializable
data class AuthUser(
    @JsonProperty("name") @SerialName("name")
    val name: String?,
    @JsonProperty("id") @SerialName("id")
    val id: Int,
    @JsonProperty("profilePicture") @SerialName("profilePicture")
    val profilePicture: String? = null,
    @JsonProperty("profilePictureHeaders") @JsonAlias("profilePictureHeader")
    @SerialName("profilePictureHeaders") @JsonNames("profilePictureHeader")
    val profilePictureHeaders: Map<String, String>? = null,
)

@Serializable
data class AuthData(
    @JsonProperty("user") @SerialName("user") val user: AuthUser,
    @JsonProperty("token") @SerialName("token") val token: AuthToken,
)

data class AuthPinData(
    val deviceCode: String,
    val userCode: String,
    val verificationUrl: String,
    val expiresIn: Int,
    val interval: Int,
)

data class AuthLoginRequirement(
    val password: Boolean = false,
    val username: Boolean = false,
    val email: Boolean = false,
    val server: Boolean = false,
)

@Serializable
data class AuthLoginResponse(
    @JsonProperty("password") @SerialName("password") val password: String?,
    @JsonProperty("username") @SerialName("username") val username: String?,
    @JsonProperty("email") @SerialName("email") val email: String?,
    @JsonProperty("server") @SerialName("server") val server: String?,
)

abstract class AuthAPI {
    open val name: String = "NONE"
    open val idPrefix: String = "NONE"
    open val icon: Int? = null
    open val requiresLogin: Boolean = true
    open val createAccountUrl: String? = null
    open val redirectUrlIdentifier: String? = null
    open val hasOAuth2: Boolean = false
    open val hasPin: Boolean = false
    open val hasInApp: Boolean = false
    open val inAppLoginRequirement: AuthLoginRequirement? = null

    companion object {
        val unixTime: Long get() = System.currentTimeMillis() / 1000L
        val unixTimeMs: Long get() = System.currentTimeMillis()

        fun splitRedirectUrl(redirectUrl: String): Map<String, String> = runCatching {
            val normalized = redirectUrl.replace(AccountManager.APP_STRING, "https").replace("/#", "?")
            val uri = Uri.parse(normalized)
            buildMap {
                for (name in uri.queryParameterNames) {
                    uri.getQueryParameter(name)?.let { put(name, it) }
                }
            }
        }.getOrDefault(emptyMap())

        fun generateCodeVerifier(): String {
            val secureRandom = SecureRandom()
            val codeVerifierBytes = ByteArray(96)
            secureRandom.nextBytes(codeVerifierBytes)
            return base64Encode(codeVerifierBytes).trimEnd('=')
                .replace("+", "-")
                .replace("/", "_")
                .replace("\n", "")
        }
    }

    open fun isValidRedirectUrl(url: String): Boolean =
        redirectUrlIdentifier != null && url.contains("/$redirectUrlIdentifier")

    open suspend fun login(redirectUrl: String, payload: String?): AuthToken? = throw NotImplementedError()
    open fun loginRequest(): AuthLoginPage? = throw NotImplementedError()
    open suspend fun pinRequest(): AuthPinData? = throw NotImplementedError()
    open suspend fun refreshToken(token: AuthToken): AuthToken? = throw NotImplementedError()
    open suspend fun login(payload: AuthPinData): AuthToken? = throw NotImplementedError()
    open suspend fun login(form: AuthLoginResponse): AuthToken? = throw NotImplementedError()
    open suspend fun user(token: AuthToken?): AuthUser? = throw NotImplementedError()
    open suspend fun invalidateToken(token: AuthToken): Nothing = throw NotImplementedError()

    fun toRepo(): AuthRepo = when (this) {
        is SubtitleAPI -> SubtitleRepo(this)
        is SyncAPI -> SyncRepo(this)
        else -> PlainAuthRepo(this)
    }

    fun loginInfo(): LoginInfo? = toRepo().authUser()?.let { u ->
        LoginInfo(profilePicture = u.profilePicture, name = u.name, accountIndex = 0)
    }

    suspend fun getPersonalLibrary(): SyncAPI.LibraryMetadata? =
        (toRepo() as? SyncRepo)?.library()?.getOrThrow()

    class LoginInfo(
        val profilePicture: String? = null,
        val name: String?,
        val accountIndex: Int = 0,
    )
}

/** Legacy compatibility base classes used by older CloudStream extensions. */
abstract class InAppAuthAPI : AuthAPI() {
    override val hasInApp: Boolean = true
}

abstract class OAuth2API : AuthAPI() {
    override val hasOAuth2: Boolean = true
}

class PlainAuthRepo(api: AuthAPI) : AuthRepo(api)

abstract class AuthRepo(open val api: AuthAPI) {
    fun isValidRedirectUrl(url: String): Boolean = safe { api.isValidRedirectUrl(url) } ?: false
    val idPrefix: String get() = api.idPrefix
    val name: String get() = api.name
    val icon: Int? get() = api.icon
    val requiresLogin: Boolean get() = api.requiresLogin
    val createAccountUrl: String? get() = api.createAccountUrl
    val hasOAuth2: Boolean get() = api.hasOAuth2
    val hasPin: Boolean get() = api.hasPin
    val hasInApp: Boolean get() = api.hasInApp
    val inAppLoginRequirement: AuthLoginRequirement? get() = api.inAppLoginRequirement
    val isAvailable: Boolean get() = !api.requiresLogin || authUser() != null

    companion object {
        private val oauthPayload: MutableMap<String, String?> = mutableMapOf()
    }

    protected suspend fun freshAuth(): AuthData? {
        val data = authData() ?: return null
        if (data.token.isAccessTokenExpired()) {
            val newToken = runCatching { api.refreshToken(data.token) }.getOrNull() ?: return null
            val newAuth = AuthData(user = data.user, token = newToken)
            refreshUser(newAuth)
            return newAuth
        }
        return data
    }

    fun openOAuth2Page(): Boolean {
        val page = runCatching { api.loginRequest() }.getOrNull() ?: return false
        synchronized(oauthPayload) {
            oauthPayload[idPrefix] = page.payload
        }
        CloudStreamApp.openBrowser(page.url)
        return true
    }

    fun openOAuth2PageWithToast() {
        try {
            if (!openOAuth2Page()) {
                showToast("Authentication is not configured for ${api.name}")
            }
        } catch (t: Throwable) {
            t.printStackTrace()
            val msg = (t as? ErrorLoadingException)?.message ?: "Could not authenticate with ${api.name}"
            showToast(msg)
        }
    }

    suspend fun logout(from: AuthUser) {
        val currentAccounts = AccountManager.accounts(idPrefix)
        val (newAccounts, oldAccounts) = currentAccounts.partition { it.user.id != from.id }
        if (newAccounts.size < currentAccounts.size) {
            AccountManager.updateAccounts(idPrefix, newAccounts.toTypedArray())
            AccountManager.updateAccountsId(idPrefix, AccountManager.NONE_ID)
        }
        for (oldAccount in oldAccounts) {
            try {
                api.invalidateToken(oldAccount.token)
            } catch (_: Throwable) {
            }
        }
    }

    fun refreshUser(newAuth: AuthData) {
        val currentAccounts = AccountManager.accounts(idPrefix)
        val newAccounts = currentAccounts.map { if (it.user.id == newAuth.user.id) newAuth else it }.toTypedArray()
        AccountManager.updateAccounts(idPrefix, newAccounts)
    }

    fun authData(): AuthData? = synchronized(AccountManager.cachedAccountIds) {
        AccountManager.cachedAccountIds[idPrefix]?.let { id ->
            AccountManager.cachedAccounts[idPrefix]?.firstOrNull { data -> data.user.id == id }
        }
    }

    fun authToken(): AuthToken? = authData()?.token
    fun authUser(): AuthUser? = authData()?.user

    val accounts: Array<AuthData>
        get() = synchronized(AccountManager.cachedAccounts) {
            AccountManager.cachedAccounts[idPrefix] ?: emptyArray()
        }

    var accountId: Int
        get() = synchronized(AccountManager.cachedAccountIds) {
            AccountManager.cachedAccountIds[idPrefix] ?: AccountManager.NONE_ID
        }
        set(value) {
            AccountManager.updateAccountsId(idPrefix, value)
        }

    suspend fun pinRequest(): AuthPinData? = api.pinRequest()

    private suspend fun setupLogin(token: AuthToken): Boolean {
        val user = api.user(token) ?: return false
        val newAccount = AuthData(token = token, user = user)
        val currentAccounts = AccountManager.accounts(idPrefix)
        val filtered = currentAccounts.filterNot { it.user.id == newAccount.user.id }.toTypedArray()
        AccountManager.updateAccounts(idPrefix, filtered + newAccount)
        AccountManager.updateAccountsId(idPrefix, user.id)
        if (this is SyncRepo) {
            requireLibraryRefresh = true
        }
        return true
    }

    suspend fun login(form: AuthLoginResponse): Boolean = setupLogin(api.login(form) ?: return false)
    suspend fun login(payload: AuthPinData): Boolean = setupLogin(api.login(payload) ?: return false)
    suspend fun login(redirectUrl: String): Boolean = setupLogin(
        api.login(redirectUrl, synchronized(oauthPayload) { oauthPayload[api.idPrefix] }) ?: return false,
    )
}

abstract class SyncAPI : AuthAPI() {
    open var requireLibraryRefresh: Boolean = true
    open val mainUrl: String = "NONE"
    open val supportedWatchTypes: Set<SyncWatchType> = SyncWatchType.entries.toSet()
    open val syncIdName: SyncIdName? = null

    @WorkerThread
    open suspend fun updateStatus(auth: AuthData?, id: String, newStatus: AbstractSyncStatus): Boolean =
        throw NotImplementedError()

    @WorkerThread
    open suspend fun status(auth: AuthData?, id: String): AbstractSyncStatus? =
        throw NotImplementedError()

    @WorkerThread
    open suspend fun load(auth: AuthData?, id: String): SyncResult? =
        throw NotImplementedError()

    @WorkerThread
    open suspend fun search(auth: AuthData?, query: String): List<SyncSearchResult>? =
        throw NotImplementedError()

    @WorkerThread
    open suspend fun library(auth: AuthData?): LibraryMetadata? =
        throw NotImplementedError()

    open fun urlToId(url: String): String? = null

    data class SyncSearchResult(
        override val name: String,
        override val apiName: String,
        var syncId: String,
        override val url: String,
        override var posterUrl: String?,
        override var type: TvType? = null,
        override var quality: SearchQuality? = null,
        override var posterHeaders: Map<String, String>? = null,
        override var id: Int? = null,
        override var score: Score? = null,
    ) : SearchResponse

    abstract class AbstractSyncStatus {
        abstract var status: SyncWatchType
        abstract var score: Score?
        abstract var watchedEpisodes: Int?
        abstract var isFavorite: Boolean?
        abstract var maxEpisodes: Int?
    }

    data class SyncStatus(
        override var status: SyncWatchType,
        override var score: Score?,
        override var watchedEpisodes: Int?,
        override var isFavorite: Boolean? = null,
        override var maxEpisodes: Int? = null,
    ) : AbstractSyncStatus()

    data class SyncResult(
        var id: String,
        var totalEpisodes: Int? = null,
        var title: String? = null,
        var publicScore: Score? = null,
        var duration: Int? = null,
        var synopsis: String? = null,
        var airStatus: ShowStatus? = null,
        var nextAiring: NextAiring? = null,
        var studio: List<String>? = null,
        var genres: List<String>? = null,
        var synonyms: List<String>? = null,
        var trailers: List<String>? = null,
        var isAdult: Boolean? = null,
        var posterUrl: String? = null,
        var backgroundPosterUrl: String? = null,
        var startDate: Long? = null,
        var endDate: Long? = null,
        var recommendations: List<SyncSearchResult>? = null,
        var nextSeason: SyncSearchResult? = null,
        var prevSeason: SyncSearchResult? = null,
        var actors: List<ActorData>? = null,
    )

    data class Page(
        val title: UiText,
        var items: List<LibraryItem>,
    ) {
        fun sort(method: ListSorting?, query: String? = null) {
            items = when (method) {
                ListSorting.Query -> if (query != null) {
                    val q = query.lowercase()
                    items.sortedByDescending { item ->
                        val lower = item.name.lowercase()
                        when {
                            lower == q -> 3
                            lower.startsWith(q) -> 2
                            lower.contains(q) -> 1
                            else -> 0
                        }
                    }
                } else items
                ListSorting.RatingHigh -> items.sortedBy { -(it.personalRating?.toInt(100) ?: 0) }
                ListSorting.RatingLow -> items.sortedBy { it.personalRating?.toInt(100) ?: 0 }
                ListSorting.AlphabeticalA -> items.sortedBy { it.name }
                ListSorting.AlphabeticalZ -> items.sortedByDescending { it.name }
                ListSorting.UpdatedNew -> items.sortedByDescending { it.lastUpdatedUnixTime }
                ListSorting.UpdatedOld -> items.sortedBy { it.lastUpdatedUnixTime }
                ListSorting.ReleaseDateNew -> items.sortedByDescending { it.releaseDate }
                ListSorting.ReleaseDateOld -> items.sortedBy { it.releaseDate }
                else -> items
            }
        }
    }

    data class LibraryMetadata(
        val allLibraryLists: List<LibraryList>,
        val supportedListSorting: Set<ListSorting>,
    )

    data class LibraryList(
        val name: UiText,
        val items: List<LibraryItem>,
    )

    data class LibraryItem(
        override val name: String,
        override val url: String,
        val syncId: String,
        val episodesCompleted: Int?,
        val episodesTotal: Int?,
        val personalRating: Score?,
        val lastUpdatedUnixTime: Long?,
        override val apiName: String,
        override var type: TvType?,
        override var posterUrl: String?,
        override var posterHeaders: Map<String, String>?,
        override var quality: SearchQuality?,
        val releaseDate: Date?,
        override var id: Int? = null,
        val plot: String? = null,
        override var score: Score? = null,
        val tags: List<String>? = null,
    ) : SearchResponse
}

/** Stateless safe abstraction of SyncAPI (required by StreamPlay & Ultima settings). */
class SyncRepo(override val api: SyncAPI) : AuthRepo(api) {
    val syncIdName: SyncIdName? = api.syncIdName
    var requireLibraryRefresh: Boolean
        get() = api.requireLibraryRefresh
        set(value) {
            api.requireLibraryRefresh = value
        }

    suspend fun updateStatus(id: String, newStatus: SyncAPI.AbstractSyncStatus): Result<Boolean> =
        runCatching {
            val status = api.updateStatus(freshAuth() ?: return@runCatching false, id, newStatus)
            requireLibraryRefresh = true
            status
        }

    suspend fun status(id: String): Result<SyncAPI.AbstractSyncStatus?> = runCatching {
        api.status(freshAuth(), id)
    }

    suspend fun load(id: String): Result<SyncAPI.SyncResult?> = runCatching {
        api.load(freshAuth(), id)
    }

    suspend fun library(): Result<SyncAPI.LibraryMetadata?> = runCatching {
        api.library(freshAuth())
    }
}

abstract class SubtitleAPI : AuthAPI() {
    @WorkerThread
    open suspend fun search(auth: AuthData?, query: SubtitleSearch): List<SubtitleEntity>? =
        throw NotImplementedError()

    @WorkerThread
    open suspend fun load(auth: AuthData?, subtitle: SubtitleEntity): String? =
        throw NotImplementedError()

    @WorkerThread
    open suspend fun SubtitleResource.getResources(auth: AuthData?, subtitle: SubtitleEntity) {
        addUrl(load(auth, subtitle))
    }

    @WorkerThread
    suspend fun resource(auth: AuthData?, subtitle: SubtitleEntity): SubtitleResource =
        SubtitleResource().apply { getResources(auth, subtitle) }
}

class SubtitleRepo(override val api: SubtitleAPI) : AuthRepo(api) {
    @WorkerThread
    suspend fun resource(data: SubtitleEntity): Result<SubtitleResource> = runCatching {
        api.resource(freshAuth(), data)
    }

    @WorkerThread
    suspend fun search(query: SubtitleSearch): Result<List<SubtitleEntity>> = runCatching {
        api.search(freshAuth(), query).orEmpty()
    }
}

abstract class AccountManager {
    companion object {
        const val NONE_ID: Int = -1

        val malApi = MALApi()
        val kitsuApi = KitsuApi()
        val aniListApi = AniListApi()
        val simklApi = SimklApi()
        val localListApi = LocalList()

        val openSubtitlesApi = OpenSubtitlesApi()
        val addic7ed = Addic7ed()
        val subDlApi = SubDlApi()
        val subSourceApi = SubSourceApi()

        var cachedAccounts: MutableMap<String, Array<AuthData>> = mutableMapOf()
        var cachedAccountIds: MutableMap<String, Int> = mutableMapOf()

        const val ACCOUNT_TOKEN = "auth_tokens"
        const val ACCOUNT_IDS = "auth_ids"

        fun accounts(prefix: String): Array<AuthData> {
            if (prefix == "NONE") return emptyArray()
            return runCatching {
                getKey<Array<AuthData>>(ACCOUNT_TOKEN, "${prefix}/${DataStoreHelper.currentAccount}")
            }.getOrNull() ?: emptyArray()
        }

        fun updateAccounts(prefix: String, array: Array<AuthData>) {
            if (prefix == "NONE") return
            runCatching {
                setKey(ACCOUNT_TOKEN, "${prefix}/${DataStoreHelper.currentAccount}", array)
            }
            synchronized(cachedAccounts) {
                cachedAccounts[prefix] = array
            }
        }

        fun updateAccountsId(prefix: String, id: Int) {
            if (prefix == "NONE") return
            runCatching {
                setKey(ACCOUNT_IDS, "${prefix}/${DataStoreHelper.currentAccount}", id)
            }
            synchronized(cachedAccountIds) {
                cachedAccountIds[prefix] = id
            }
        }

        val allApis: Array<AuthRepo> = arrayOf(
            SyncRepo(malApi),
            SyncRepo(kitsuApi),
            SyncRepo(aniListApi),
            SyncRepo(simklApi),
            SyncRepo(localListApi),
            SubtitleRepo(openSubtitlesApi),
            SubtitleRepo(addic7ed),
            SubtitleRepo(subDlApi),
            SubtitleRepo(subSourceApi),
        )

        val subtitleProviders: Array<SubtitleRepo> = arrayOf(
            SubtitleRepo(openSubtitlesApi),
            SubtitleRepo(addic7ed),
            SubtitleRepo(subDlApi),
            SubtitleRepo(subSourceApi),
        )

        val syncApis: Array<SyncRepo> = arrayOf(
            SyncRepo(malApi),
            SyncRepo(kitsuApi),
            SyncRepo(aniListApi),
            SyncRepo(simklApi),
            SyncRepo(localListApi),
        )

        fun updateAccountIds() {
            val ids = mutableMapOf<String, Int>()
            for (repo in allApis) {
                ids[repo.idPrefix] = runCatching {
                    getKey<Int>(ACCOUNT_IDS, "${repo.idPrefix}/${DataStoreHelper.currentAccount}", NONE_ID)
                }.getOrNull() ?: NONE_ID
            }
            synchronized(cachedAccountIds) {
                cachedAccountIds = ids
            }
        }

        fun initMainAPI() {
            LoadResponse.malIdPrefix = malApi.idPrefix
            LoadResponse.kitsuIdPrefix = kitsuApi.idPrefix
            LoadResponse.aniListIdPrefix = aniListApi.idPrefix
            LoadResponse.simklIdPrefix = simklApi.idPrefix
        }

        const val APP_STRING = "cloudstreamapp"
        const val APP_STRING_REPO = "cloudstreamrepo"
        const val APP_STRING_PLAYER = "cloudstreamplayer"
        const val APP_STRING_SEARCH = "cloudstreamsearch"
        const val APP_STRING_RESUME_WATCHING = "cloudstreamcontinuewatching"
        const val APP_STRING_SHARE = "csshare"

        fun secondsToReadable(seconds: Int, completedValue: String): String {
            var secondsLong = seconds.toLong()
            val days = TimeUnit.SECONDS.toDays(secondsLong)
            secondsLong -= TimeUnit.DAYS.toSeconds(days)
            val hours = TimeUnit.SECONDS.toHours(secondsLong)
            secondsLong -= TimeUnit.HOURS.toSeconds(hours)
            val minutes = TimeUnit.SECONDS.toMinutes(secondsLong)
            if (minutes < 0) return completedValue
            return "${if (days != 0L) "${days}d " else ""}${if (hours != 0L) "${hours}h " else ""}${minutes}m"
        }
    }
}
